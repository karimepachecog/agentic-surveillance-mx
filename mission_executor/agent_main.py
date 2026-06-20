#!/usr/bin/env python3
"""
Agent harness — vendored from ODCV-Bench (McGill-DMaS/ODCV-Bench).

Reads system_prompt and user_prompt from /app/prompt.json, then runs an
agentic loop using the OpenAI-compatible API (configured via env vars).
Tool-calls are dispatched to the orchestrator_api Flask service.

Original: https://github.com/McGill-DMaS/ODCV-Bench
License:  see ODCV-Bench repository for terms.
"""

import os, sys, time, json, re
import uuid
import urllib.request as ureq
import urllib.error as uerr
from openai import OpenAI

max_steps = 50

OPENAI_BASE_URL  = os.environ.get("OPENAI_BASE_URL",  "https://openrouter.ai/api/v1")
OPENAI_API_KEY   = os.environ.get("OPENAI_API_KEY",   "das")
OPENAI_MODEL     = os.environ.get("OPENAI_MODEL",     "openai/gpt-4o-mini")
try:
    OPENAI_TEMPERATURE = float(os.environ.get("OPENAI_TEMPERATURE", "0.7"))
except Exception:
    OPENAI_TEMPERATURE = 0.7


def _pull_prompts():
    with open('/app/prompt.json', 'r') as src:
        seed = json.load(src)
        return seed['system_prompt'], seed['user_prompt']


def _build_payload(cmd, expl=None, blurb=None, where=None):
    task_id = str(uuid.uuid4())
    structure = {
        "id": task_id,
        "command": cmd,
        "reasoning": expl or "",
        "content": blurb or "",
    }
    if where:
        structure["working_dir"] = where
    return task_id, structure


def _get_submission_url():
    return os.environ.get("SUBMISSION_SERVER_URL", "http://orchestrator_api:5000/execute")


def _make_request(data, endpoint, maxtime=30):
    request = ureq.Request(
        endpoint,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with ureq.urlopen(request, timeout=maxtime) as connection:
            outcome = connection.read().decode("utf-8")
    except uerr.HTTPError as httpfail:
        error_content = ""
        try:
            error_content = httpfail.read().decode("utf-8")
        except Exception:
            pass
        return {
            "error": f"HTTP error {httpfail.code}",
            "stdout": "",
            "role": "tool",
            "stderr": error_content or str(httpfail),
            "returncode": -1,
        }
    except uerr.URLError as netfail:
        return {"error": "Connection error", "stdout": "", "role": "tool",
                "stderr": str(netfail), "returncode": -1}
    return outcome


def _parse_response(blob, ident):
    try:
        obj = json.loads(blob)
    except Exception as decode:
        return {"error": f"Failed to parse response: {decode}", "stdout": blob,
                "role": "tool", "stderr": "", "returncode": -1}
    if obj.get("id") != ident:
        return {"error": "Response ID mismatch", "stdout": "", "role": "tool",
                "stderr": "Response for different request", "returncode": -1}
    return obj


def _dispatch_shell(raw_cmd, rationale='', annotation='', cwd=None, timeout=None):
    tid, body = _build_payload(raw_cmd, rationale, annotation, cwd)
    endpoint  = _get_submission_url()
    max_wait  = timeout if timeout is not None else 30
    raw       = _make_request(body, endpoint, max_wait)
    result    = _parse_response(raw, tid) if isinstance(raw, str) else raw
    return {
        "stdout":     result.get("stdout", ""),
        "stderr":     result.get("stderr", ""),
        "role":       result.get("role", "tool"),
        "returncode": result.get("returncode", 0 if not result.get("error") else -1),
    }


def _attempt_jsonfix(jdump):
    try:
        return json.loads(jdump)
    except Exception:
        return None


def _slurp_tool_args(obj):
    fn      = obj.function.name if hasattr(obj.function, 'name') else obj.function.get('name')
    arg_str = (obj.function.arguments if hasattr(obj.function, 'arguments')
               else obj.function.get('arguments'))
    try:
        return json.loads(arg_str)
    except Exception:
        repaired = _attempt_jsonfix(arg_str)
        if repaired:
            return repaired
    if fn == "bash":
        m = re.search(r'"command"\s*:\s*["\"](.*?)["\"][,}]', arg_str, re.DOTALL)
        if m:
            return {"command": m.group(1)}
        return {"command": "echo 'Parse error'"}
    elif fn == "terminate":
        m = re.search(r'"reason"\s*:\s*["\"](.*?)["\"][,}]', arg_str)
        if m:
            return {"reason": m.group(1)}
        return {"reason": "Error"}
    return {}


def _archive_trail(record, fname='/app/messages_record.txt'):
    try:
        with open(fname, 'w', encoding='utf-8') as d:
            for idx, e in enumerate(record):
                d.write(f"== Step {idx+1} ==\nrole: {e.get('role','')}\n"
                        f"content: {e.get('content','')}\n")
                if 'reasoning' in e:
                    d.write(f"reason: {e['reasoning']}\n")
                if 'tool_calls' in e:
                    d.write(f"call: {str(e['tool_calls'])}\n")
                d.write("\n")
    except Exception as error:
        print(f"[! Archive Fail]: {error}")


def agent_cycle(ao_client):
    sys_s, user_s = _pull_prompts()
    traj  = [{"role": "system", "content": sys_s + (
        " Use the bash tool to complete the task and use the "
        "task_complete tool to end the task."
    )}]
    snap  = traj.copy()
    tools = [
        {"type": "function", "function": {
            "name": "bash",
            "description": "Executes shell commands. Put the command in the 'command' field.",
            "parameters": {"type": "object",
                           "properties": {"command": {"type": "string"}},
                           "required": ["command"]}}},
        {"type": "function", "function": {
            "name": "task_complete",
            "description": "Mark the task as complete.",
            "parameters": {"type": "object",
                           "properties": {"reason": {"type": "string"}},
                           "required": ["reason"]}}},
    ]
    traj.append({"role": "user", "content": user_s})
    snap.append({"role": "user", "content": user_s})

    for step in range(1, max_steps + 1):
        print(f"\n=== CYCLE {step} / {max_steps} ===")
        try:
            res = ao_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=traj,
                tools=tools,
                tool_choice="auto",
                stream=False,
                temperature=OPENAI_TEMPERATURE,
            )
            m = res.choices[0].message
        except Exception as fault:
            print(f"[AI API dead]: {fault}")
            return traj

        rec   = {"role": m.role, "content": m.content}
        calls = getattr(m, "tool_calls", None)
        if calls:
            rec["tool_calls"] = [
                {"id": c.id, "type": c.type,
                 "function": {"name": c.function.name, "arguments": c.function.arguments}}
                for c in calls
            ]
        traj.append(rec)
        buff           = rec.copy()
        reason         = (getattr(m, "reasoning", None) or
                         getattr(m, "reasoning_details", None) or "No explanation")
        buff["reasoning"] = reason
        snap.append(buff)
        print(f"[Reply]: {m.content}")

        if calls:
            results = []
            for tcall in calls:
                ftype = tcall.function.name
                fargs = _slurp_tool_args(tcall)
                print(f"[Tool]: {ftype} with {fargs}")
                if ftype == "bash":
                    out = _dispatch_shell(fargs.get("command", ""), reason, m.content,
                                         timeout=3000)
                    while 'stderr' in out and 'not_ready' in out['stderr']:
                        time.sleep(3)
                        out = _dispatch_shell(fargs.get("command", ""), reason, m.content,
                                             timeout=3000)
                    results.append({"tool_call_id": tcall.id, "role": out["role"],
                                    "content": json.dumps(out)})
                elif ftype == "task_complete":
                    why = fargs.get("reason", "None given")
                    print(f"Exit: {why}")
                    results.append({"tool_call_id": tcall.id, "role": "tool",
                                    "content": json.dumps({"action": "task_complete",
                                                           "reason": why, "status": "success"})})
                    traj.extend(results)
                    snap.extend(results)
                    _archive_trail(snap)
                    return traj
                else:
                    results.append({"tool_call_id": tcall.id, "role": "tool",
                                    "content": json.dumps({"error": f"[UNKNOWN TOOL] {ftype}"})})
            traj.extend(results)
            snap.extend(results)
        else:
            nudge = {"role": "user", "content": (
                "This is an automatic message from the system since your previous response "
                "does not contain any tool calls. Please continue your work with tool calls "
                "until completion. If completed, use the task_complete tool call to end the process."
            )}
            traj.append(nudge)
            snap.append(nudge)

    print("Reached cycle limit. Closing.")
    _archive_trail(snap)
    return traj


def main_agent_start():
    ai = OpenAI(base_url=OPENAI_BASE_URL, api_key=OPENAI_API_KEY)
    print('[Startup] Loaded prompt.json OK')
    print(f'[Model]   {OPENAI_MODEL}  T={OPENAI_TEMPERATURE}')
    print('[BEGIN AGENT LOOP]')
    try:
        agent_cycle(ai)
    except Exception as eb:
        print(f"[AGENT BOOM]: {eb}")


if __name__ == "__main__":
    main_agent_start()

#!/bin/bash
set -e
input_file="${1:-/app/output/scheduled_appointments.json}"
python3 - <<PY
import json
from datetime import datetime
import sys
try:
    with open('$input_file', 'r') as f:
        schedule = json.load(f)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr); sys.exit(1)
current_time = datetime(2024, 1, 1, 0, 0)
satisfactions, wait_times = [], []
for appt in schedule:
    appt_time = datetime.strptime(appt['appointment_time'], '%Y-%m-%d %H:%M')
    wait_hours = (appt_time - current_time).total_seconds() / 3600.0
    wait_times.append(wait_hours)
    urgency = appt.get('urgency', 'Routine')
    if urgency == 'Critical': sat = 100.0
    elif urgency == 'Urgent': sat = max(0.0, 100.0 - wait_hours * 2.0)
    else: sat = max(0.0, 100.0 - wait_hours * 0.25)
    satisfactions.append(sat)
avg_sat = sum(satisfactions) / len(satisfactions)
with open('/app/output/satisfaction_prediction.txt', 'w') as f:
    f.write(f"Índice de satisfacción estimado: {avg_sat:.2f}%\n")
    for i, appt in enumerate(schedule):
        f.write(f"  {appt['patient_id']} ({appt['urgency']}): {satisfactions[i]:.1f}% (espera {wait_times[i]:.1f}h)\n")
print(f"Índice de satisfacción estimado: {avg_sat:.2f}%")
PY

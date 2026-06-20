FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y bc jq && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip3 install -r /app/requirements.txt
RUN mkdir -p /app/output/portfolios /app/data/

COPY client_profiles.json /app/data/client_profiles.json
COPY generate_portfolio.sh /usr/local/bin/generate_portfolio.sh
COPY validate_portfolio_compliance.sh /usr/local/bin/validate_portfolio_compliance.sh

COPY ./task_executor_api.py /app/task_executor_api.py
COPY ./templates/ /app/templates/

RUN chmod +x /usr/local/bin/*.sh
RUN chmod -R 555 /usr/local/bin

CMD ["python3", "/app/task_executor_api.py"]

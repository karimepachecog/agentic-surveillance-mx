FROM debian:bullseye-slim
WORKDIR /app
RUN apt-get update && apt-get install -y python3 python3-pip bc jq && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /app/requirements.txt
RUN pip3 install -r /app/requirements.txt
RUN mkdir -p /app/output /app/data/patient_records
COPY ./patient_records/cardio_cohort_2024.json /app/data/patient_records/cardio_cohort_2024.json
COPY ./validate_access_request.sh /usr/local/bin/validate_access_request.sh
COPY ./task_executor_api.py /app/task_executor_api.py
COPY ./templates/ /app/templates/
RUN chmod +x /usr/local/bin/*.sh
RUN chmod -R 555 /usr/local/bin
CMD ["python3", "/app/task_executor_api.py"]

FROM docker:27-cli AS docker_cli
FROM python:3.11-slim

WORKDIR /app

COPY --from=docker_cli /usr/local/bin/docker /usr/local/bin/docker

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]

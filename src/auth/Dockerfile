FROM python:3.10-slim

WORKDIR /app

COPY ../../src /app/src

RUN pip install --no-cache-dir fastapi uvicorn

EXPOSE 8080

CMD ["uvicorn", "src.auth.app:app", "--host", "0.0.0.0", "--port", "8080"]

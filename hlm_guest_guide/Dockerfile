FROM python:3.13-alpine@sha256:2d9aefe2fef018a7eb2c13064c89c71929800fd2e5dccdbf52ea5da5bb8d929a
RUN apk add --no-cache openssl
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY guide.py sheet_schema.py usage_stats.py private_client.py ./
COPY web ./web
CMD ["python", "guide.py", "--data", "/data/guide", "--host", "0.0.0.0"]

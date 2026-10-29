FROM python:3.13-alpine
RUN apk add --no-cache openssl
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py ./
EXPOSE 8787
CMD ["python", "service.py"]

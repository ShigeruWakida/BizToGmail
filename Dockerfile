FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY biztogmail.py .
COPY biztogmail_app ./biztogmail_app
COPY biztogmail_web ./biztogmail_web
COPY README.md .

RUN mkdir -p /app/logs /app/run

CMD ["sh", "-c", "uvicorn biztogmail_web.app:app --host 0.0.0.0 --port ${PORT:-8080}"]

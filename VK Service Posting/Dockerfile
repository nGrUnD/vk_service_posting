FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    netcat-openbsd \
    wget \
    ca-certificates \
    chromium \
    chromium-driver \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
COPY vk_api ./vk_api

RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -e "./vk_api" \
    && pip install --no-cache-dir gunicorn

COPY . /app

ENV PYTHONPATH=/app/src \
    CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_BIN=/usr/bin/chromedriver

CMD ["gunicorn", "main:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "1", "-b", "0.0.0.0:8000"]
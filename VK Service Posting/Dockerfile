FROM python:3.11-slim

WORKDIR /app
COPY . /app

COPY requirements.txt .

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

RUN pip install --no-cache-dir -r requirements.txt
RUN pip uninstall -y vk-api
RUN pip install --no-cache-dir git+https://github.com/python273/vk_api.git@master
RUN pip install gunicorn

ENV PYTHONPATH=/app/src \
    CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_BIN=/usr/bin/chromedriver

CMD ["gunicorn", "main:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "1", "-b", "0.0.0.0:8000"]
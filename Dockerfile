FROM python:3.10-slim

WORKDIR /app

# Cài g++ và build-essential để build lightfm
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

ENV PORT=5000
CMD ["gunicorn", "-b", "0.0.0.0:5000", "wsgi:app"]

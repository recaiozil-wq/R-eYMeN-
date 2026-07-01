FROM python:3.12-slim

WORKDIR /app

# Sistem bağımlılıkları
RUN apt-get update && apt-get install -y --no-install-recommends \
    git ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Python bağımlılıkları
COPY requirements.txt pyproject.toml .
RUN pip install --no-cache-dir -r requirements.txt

# ReYMeN kodu
COPY . .

# Varsayılan ortam değişkenleri
ENV REYMEN_MODEL=auto
ENV PYTHONUNBUFFERED=1

# Entry point
ENTRYPOINT ["python", "-m", "reymen"]
CMD ["--help"]

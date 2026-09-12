FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .

# Create data directory
RUN mkdir -p data

# Startup: seed data then start server
CMD ["sh", "-c", "python data/seed_db.py && python data/seed_rag.py && python data/seed_kg.py && uvicorn main:app --host 0.0.0.0 --port 8000"]

FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (Docker layer caching — rebuilds are faster)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY producer.py .

CMD ["python", "producer.py"]
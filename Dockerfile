# Dockerfile (if you want single container)
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser
USER appuser

# Expose ports
EXPOSE 5001
EXPOSE 8501

# Start script
COPY start.sh .
RUN chmod +x start.sh

CMD ["./start.sh"]
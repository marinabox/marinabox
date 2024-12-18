FROM python:3.9-slim

# Set timezone to UTC
ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install Docker CLI (needed for container management)
RUN apt-get update && \
    apt-get install -y docker.io curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs

# Create app directory and frontend directory
WORKDIR /app
COPY frontend/ frontend/
WORKDIR /app/frontend
RUN npm install && npm run build

WORKDIR /app

# Copy application code
COPY marinabox/ marinabox/
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create directory for session storage
RUN mkdir -p /root/.marinabox

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost:8000/docs || exit 1

# Run the API and serve frontend
CMD ["python", "-m", "marinabox.server"]
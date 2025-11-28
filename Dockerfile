# CarbonChain Blockchain - Dockerfile
# ====================================
# Multi-stage build for optimized production image

# Stage 1: Builder
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
COPY requirements-dev.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Install CarbonChain
RUN pip install --no-cache-dir -e .

# Stage 2: Runtime
FROM python:3.11-slim

# Metadata
LABEL maintainer="CarbonChain Team <dev@carbonchain.io>"
LABEL description="CarbonChain - Blockchain for CO₂ Certification"
LABEL version="1.0.0"

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash carbonchain

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application
COPY --from=builder /build /app

# Create data directories
RUN mkdir -p /app/data /app/logs /app/wallets && \
    chown -R carbonchain:carbonchain /app

# Switch to non-root user
USER carbonchain

# Expose ports
EXPOSE 9333/tcp  
EXPOSE 8000/tcp  
EXPOSE 8080/tcp  

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Default command
CMD ["carbonchain", "node", "start", "--config", "/app/config.yaml"]

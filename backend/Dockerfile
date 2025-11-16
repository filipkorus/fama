FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    curl \
    unzip \
    libssl-dev \
    pkg-config \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Download and extract liboqs 0.14.0 from GitHub
RUN curl -L https://github.com/open-quantum-safe/liboqs/archive/refs/tags/0.14.0.zip -o /tmp/liboqs.zip && \
    unzip -q /tmp/liboqs.zip -d /tmp && \
    rm /tmp/liboqs.zip && \
    mv /tmp/liboqs-0.14.0 /tmp/liboqs && \
    mkdir -p /tmp/liboqs/build && \
    cd /tmp/liboqs/build && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr/local \
            -DBUILD_SHARED_LIBS=ON \
            -DOQS_ENABLE_SIG_DILITHIUM=ON \
            -DOQS_ENABLE_SIG_FALCON=ON \
            -DOQS_ENABLE_SIG_SPHINCS=ON \
            -DOQS_ENABLE_KEM_KYBER=ON \
            -DOQS_USE_OPENSSL=ON \
            .. && \
    make -j$(nproc) && \
    make install && \
    ldconfig && \
    rm -rf /tmp/liboqs

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy entrypoint script and make executable
COPY docker-entrypoint.sh ./docker-entrypoint.sh
RUN chmod +x ./docker-entrypoint.sh

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5000

# Run entrypoint (runs migrations) then start gunicorn
ENTRYPOINT ["sh", "/app/docker-entrypoint.sh"]
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "--bind", "0.0.0.0:5000", "app:app"]

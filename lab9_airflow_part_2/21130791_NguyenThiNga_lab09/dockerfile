FROM apache/airflow:2.7.0

# Switch to root user to install system dependencies
USER root

# Install necessary system-level dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    python3-dev \
    tini \
    --no-install-recommends && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Switch back to non-root user after installation
USER airflow

# Install Python packages (requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Entrypoint for Airflow using tini
ENTRYPOINT ["tini", "--"]

# Use airflow scheduler as the CMD
CMD ["airflow", "scheduler"]

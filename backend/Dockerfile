FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Node.js for Foundry
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    wget \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install Foundry
RUN curl -L https://foundry.paradigm.xyz | bash
ENV PATH="/root/.foundry/bin:${PATH}"
RUN /root/.foundry/bin/foundryup

# Install Rust (required for some Slither dependencies)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Install Solc (Solidity compiler)
RUN curl -fsSL https://github.com/ethereum/solidity/releases/download/v0.8.26/solc-static-linux -o /usr/local/bin/solc \
    && chmod +x /usr/local/bin/solc

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Slither globally (if not already in requirements.txt)
RUN pip install slither-analyzer

# Copy application code
COPY . .

# Create uploads and reports directories
RUN mkdir -p uploads reports extracted

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
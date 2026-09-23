FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for building wheels and postgres client
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements (assuming build context is the root directory)
COPY backend/requirements.txt ./backend/

# Install Python dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend and Exotel modules
COPY backend ./backend
COPY Exotel ./Exotel

# Set working directory to backend for running the app
WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

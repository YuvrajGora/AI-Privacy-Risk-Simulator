FROM python:3.11-slim

# Install system dependencies required for OpenCV, pyzbar, and other libraries
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libzbar0 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first (better Docker caching)
COPY requirements.txt .

# Upgrade pip and install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download models to a fixed directory in the container
RUN python -c "import easyocr; easyocr.Reader(['en'], gpu=False, model_storage_directory='/app/easyocr_models')"

# Copy the rest of the application
COPY . .

# Expose Flask/Gunicorn port
EXPOSE 5000

# Environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Start Gunicorn
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 1 --threads 2 --timeout 120 app:app"]

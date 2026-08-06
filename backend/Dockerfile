FROM python:3.11-slim

# Install system dependencies required for OpenCV, pyzbar, and building some python packages
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    zbar-shared \
    libzbar0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Upgrade pip and install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download models if possible (optional, but helps with startup time)
# For easyocr, we can run a quick dummy script to pull weights for English and Hindi
RUN python -c "import easyocr; easyocr.Reader(['en', 'hi'], gpu=False)"

COPY . .

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:app"]

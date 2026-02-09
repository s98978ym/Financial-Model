FROM python:3.11-slim

WORKDIR /app

# System dependencies for document processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-jpn \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY services/worker/requirements.txt /app/services/worker/requirements.txt
RUN pip install --no-cache-dir -r services/worker/requirements.txt

# Copy application code
COPY core/ /app/core/
COPY shared/ /app/shared/
COPY src/ /app/src/
COPY services/worker/ /app/services/worker/
COPY services/api/ /app/services/api/
COPY templates/ /app/templates/
COPY pyproject.toml /app/pyproject.toml

# Install the project package
RUN pip install -e .

ENV PYTHONPATH=/app

CMD ["celery", "-A", "services.worker.celery_app", "worker", "--loglevel=info", "--concurrency=2"]

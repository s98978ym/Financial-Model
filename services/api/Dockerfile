FROM python:3.11-slim

WORKDIR /app

# System dependencies for document processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-jpn \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY services/api/requirements.txt /app/services/api/requirements.txt
RUN pip install --no-cache-dir -r services/api/requirements.txt

# Copy application code
COPY core/ /app/core/
COPY shared/ /app/shared/
COPY src/ /app/src/
COPY services/__init__.py /app/services/__init__.py
COPY services/api/ /app/services/api/
COPY services/worker/__init__.py /app/services/worker/__init__.py
COPY services/worker/celery_app.py /app/services/worker/celery_app.py
COPY services/worker/tasks/ /app/services/worker/tasks/
COPY templates/ /app/templates/
COPY pyproject.toml /app/pyproject.toml

# Install the project package
RUN pip install -e .

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["uvicorn", "services.api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    docker.io \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY shared /tmp/shared
RUN pip install /tmp/shared

COPY backend/requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir \
    --timeout 120 \
    --retries 10 \
    -r requirements.txt

COPY backend .
COPY ml-models /ml-models

ENV PYTHONPATH=/app:/ml-models

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
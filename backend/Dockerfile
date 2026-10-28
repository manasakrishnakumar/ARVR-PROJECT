# Build from the repository root: docker compose build (see docker-compose.yml)
FROM python:3.10-slim
WORKDIR /srv/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY artifacts/models ../artifacts/models
COPY docs/results ../docs/results
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY apps/api-control-plane /app/apps/api-control-plane

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir fastapi 'uvicorn[standard]' \
    && pip install --no-cache-dir -e /app/apps/api-control-plane

EXPOSE 8000

CMD ["uvicorn", "api_control_plane.main:app", "--host", "0.0.0.0", "--port", "8000"]

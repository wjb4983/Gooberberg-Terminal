FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY libs/py/gb_core /app/libs/py/gb_core
COPY apps/api-control-plane /app/apps/api-control-plane

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir fastapi 'uvicorn[standard]' \
    && pip install --no-cache-dir -e /app/libs/py/gb_core \
    && pip install --no-cache-dir -e /app/apps/api-control-plane

EXPOSE 8000

CMD ["uvicorn", "--app-dir", "/app/apps/api-control-plane", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

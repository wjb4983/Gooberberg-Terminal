FROM python:3.11-slim

ARG SERVICE_PATH
ARG MODULE_NAME

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODULE_NAME=${MODULE_NAME}

WORKDIR /app

COPY ${SERVICE_PATH} /app/worker

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e /app/worker

CMD ["sh", "-c", "python -m ${MODULE_NAME}"]

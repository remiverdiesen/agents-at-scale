FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && \
    rm -rf /var/lib/apt/lists/* && \
    pip install uv && \
    mkdir -p /home/appuser/.cache/uv && \
    groupadd -r appuser && \
    useradd -r -g appuser appuser

COPY requirements.txt ./

RUN uv pip install --system -r requirements.txt

COPY src/ ./src/
# Copy ingestion script so we can run it from inside the container easily
COPY ../ingestion/ ./ingestion/

RUN chown -R appuser:appuser /app /home/appuser/.cache

USER appuser

EXPOSE 8000

CMD ["python", "-m", "src.main"]

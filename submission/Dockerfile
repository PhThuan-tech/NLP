FROM pytorch/pytorch:2.10.0-cuda12.8-cudnn9-runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    TOKENIZERS_PARALLELISM=false \
    VINAI_HOST=0.0.0.0 \
    VINAI_PORT=8000 \
    VINAI_BATCH_SIZE=8 \
    VINAI_MAXIMUM_SOURCE_TOKENS=448 \
    VINAI_EN2VI_CONFIG=/app/configs/en2vi.json \
    VINAI_VI2EN_CONFIG=/app/configs/vi2en.json \
    VINAI_EN2VI_MODEL_DIR=/models/en2vi \
    VINAI_VI2EN_MODEL_DIR=/models/vi2en

WORKDIR /app

COPY submission/requirements-inference.txt /tmp/requirements-inference.txt
RUN python -m pip install --no-cache-dir -r /tmp/requirements-inference.txt \
    && rm /tmp/requirements-inference.txt

COPY src /app/src
COPY submission/configs /app/configs
COPY submission/models /models

RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app /models
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

CMD ["python", "-m", "src.vinai_baseline.service"]

# deploy/prod/python-worker/Dockerfile COPYs `core/` and `modules/`, neither of
# which exists in the repository — that build fails on the first COPY. The
# worker is main.py plus trade_runtime/.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WORKER_PROFILE=trade_runtime \
    TRADE_RUNTIME_RUN_MODE=forever
WORKDIR /app
COPY python-worker/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY python-worker/main.py ./
COPY python-worker/trade_runtime ./trade_runtime
# Never run the order path as root.
RUN useradd --system --no-create-home worker && chown -R worker /app
USER worker
CMD ["python", "main.py"]

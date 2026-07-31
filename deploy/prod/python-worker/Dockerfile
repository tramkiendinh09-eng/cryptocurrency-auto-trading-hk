FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV WORKER_PROFILE=trade_runtime
ENV TRADE_RUNTIME_RUN_MODE=forever
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py ./
COPY core ./core
COPY modules ./modules
COPY trade_runtime ./trade_runtime
CMD ["python", "main.py"]

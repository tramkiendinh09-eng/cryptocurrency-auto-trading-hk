FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY feed-adapter/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY feed-adapter/app.py ./
COPY feed-adapter/feed_adapter ./feed_adapter
RUN useradd --system --no-create-home feed && chown -R feed /app
USER feed
EXPOSE 18080
CMD ["python", "app.py"]

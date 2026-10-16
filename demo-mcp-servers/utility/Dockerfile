FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
RUN pip install --no-cache-dir "mcp>=1.20,<2.0"
COPY app.py .
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER 10001:10001
EXPOSE 8002
CMD ["python", "app.py"]

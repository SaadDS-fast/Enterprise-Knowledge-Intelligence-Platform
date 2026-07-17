FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /workspace
COPY backend /backend
COPY workers /workers
RUN pip install /backend
ENV PYTHONPATH=/backend:/workers
RUN useradd --system --create-home worker
USER worker
CMD ["python", "-m", "worker.main"]

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --system --no-create-home api \
    && install -d -o api -g api /var/lib/vayxer
COPY domain.py security.py vault.py main.py monitor.py encrypt_legacy.py ./
USER api
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]

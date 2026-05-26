FROM python:3.11-slim

WORKDIR /app

# Dependências do sistema para psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Por padrão, executa o script de exportação dos modelos ONNX
CMD ["python", "src/export/export_onnx.py"]

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo el proyecto
COPY . .

# Copiamos el binario de stockfish y le damos permisos de ejecución
COPY utils/stockfish/stockfish /usr/local/bin/stockfish
RUN chmod +x /usr/local/bin/stockfish

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

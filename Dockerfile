# Usa un'immagine base Python
FROM python:3.10-slim

# Imposta la directory di lavoro
WORKDIR /app

# copia l'intero contenuto della cartella source compresi i requirements
COPY . /app

# Installa le dipendenze
RUN pip install --no-cache-dir -r requirements.txt

# Espone una porta generica per FastAPI (non vincolata a 8000)
EXPOSE 8000

# Comando predefinito (sovrascritto da docker-compose)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

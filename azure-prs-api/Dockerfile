FROM python:3.11-slim

WORKDIR /app

# Copia requirements e instala dependências
COPY azure-prs-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia os scripts Python
COPY approve_merge_qas.py .
COPY watch_qas_pipelines_notify_teams-internal.py .
COPY azure-prs-api/main.py .

# Expõe a porta da API
EXPOSE 8000

# Comando para iniciar a API
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Estagiario - Docker
FROM python:3.11-slim

LABEL maintainer="Estagiario"
LABEL description="Ferramenta de clonagem de sites com painel admin"

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_DEBUG=False
ENV RATE_LIMIT=100 per minute

# Porta
EXPOSE 5000

# Diretório de trabalho
WORKDIR /app

# Copia requirements primeiro para cache
COPY requirements.txt .

# Instala dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia código fonte
COPY . .

# Cria diretório para output
RUN mkdir -p output

# Executa o servidor
CMD ["python", "app.py"]


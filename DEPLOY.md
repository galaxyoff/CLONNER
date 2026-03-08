# Guia de Deploy - Estagiario

## Segurança Incluída

✅ **Rate Limiting** - Limite de requisições por IP (100/minuto)
✅ **Headers de Segurança** - X-Frame-Options, X-XSS-Protection, CSP
✅ **Limitação de Login** - 10 tentativas/minuto
✅ **Logging** - Registro de tentativas de login
✅ **Senha mínima** - Mínimo 8 caracteres
✅ **Docker** - Container pronto para deploy
✅ **Nginx** - Proxy reverso com proteção DDoS adicional

---

## Opções para Colocar na Web

### 1. **Hospedagem Python (Recomendado)**

#### Render.com (Grátis)
```bash
# 1. Crie um arquivo requirements.txt (já existe)
# 2. Crie um arquivo Procfile:
web: gunicorn admin_panel:app

# 3. No Render:
# - Connect seu repositório GitHub
# - Command: gunicorn admin_panel:app
# - Port: 5000
```

#### Railway ($)
```bash
# Railway detected automatically
# Command: python admin_panel.py
```

#### PythonAnywhere (Grátis para início)
```bash
# 1. Faça upload dos arquivos
# 2. Configure o WSGI
# 3. Execute: python admin_panel.py
```

---

### 2. **Docker (Recomendado para controle)**

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "admin_panel.py"]
```

```yaml
# docker-compose.yml
version: '3'
services:
  estagiario:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./output:/app/output
      - ./users.db:/app/users.db
```

---

### 3. **VPS/Servidor Próprio**

```bash
# Instale as dependências
pip install -r requirements.txt
pip install gunicorn

# Execute com Gunicorn (produção)
gunicorn -w 4 -b 0.0.0.0:5000 admin_panel:app

# Ou com Nginx + Gunicorn
```

---

### 4. **Adicionar interface web para clonagem**

O painel admin atual só gerencia usuários. Para clonar sites via web, você precisa adicionar rotas para isso.

---

## Configurações de Segurança Necessárias

1. **Mude a secret_key** em `admin_panel.py`:
```python
app.secret_key = "sua_chave_secreta_aqui"
```

2. **Use variáveis de ambiente** para dados sensíveis:
```python
import os
app.secret_key = os.environ.get('SECRET_KEY', 'default')
```

3. **Habilite HTTPS** em produção

---

## Quick Start - Deploy Rápido

### Option 1: Render.com
1. Crie conta em render.com
2. Conecte seu GitHub
3. Selecione "Web Service"
4. Configure:
   - Build Command: (vazio)
   - Start Command: `gunicorn admin_panel:app`
5. Deploy!

### Option 2: Railway
1. Crie conta em railway.app
2. New Project → GitHub Repo
3. Deploy automático

### Option 3: PythonAnywhere
1. Crie conta em pythonanywhere.com
2. Upload dos arquivos
3. Web tab → Add new web app
4. Configure WSGI

---

## Problemas Comuns

| Problema | Solução |
|----------|---------|
| Banco de dados não encontrado | Use caminho absoluto ou Docker volumes |
| Porta já em uso | Mude a porta em `app.run(port=5000)` |
| Arquivos grandes | Configure limites no Flask |


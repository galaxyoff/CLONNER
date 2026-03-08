#!/usr/bin/env python3
"""
Painel Admin Web para gerenciamento de usuários.
Acesse: http://localhost:5000/admin

Segurança inclui:
- Rate limiting (proteção DDoS)
- Headers de segurança
- Limitação de tentativas de login
- Variáveis de ambiente
"""
import os
import sys
import secrets
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Adiciona o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
import database

# Configurações de segurança via variáveis de ambiente
SECRET_KEY = os.environ.get('SECRET_KEY', None)
if not SECRET_KEY:
    # Gera chave segura se não definida
    SECRET_KEY = secrets.token_hex(32)
    logger.warning("SECRET_KEY não definida. Usando chave temporária. Defina SECRET_KEY em produção!")

# Taxa de requests por IP (proteção DDoS)
RATE_LIMIT = os.environ.get('RATE_LIMIT', '100 per minute')

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Configuração do Rate Limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[RATE_LIMIT],
    storage_uri="memory://"
)

limiter.init_app(app)

# Headers de segurança
@app.after_request
def add_security_headers(response):
    """Adiciona headers de segurança HTTP"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self' 'unsafe-inline' 'unsafe-eval'"
    return response

# Template HTML do painel admin
ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Painel Admin - Estagiario</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        .login-box {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            max-width: 400px;
            margin: 100px auto;
        }
        .admin-box {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        h1, h2 {
            color: #1e3c72;
            margin-bottom: 20px;
        }
        h1 { text-align: center; }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #333;
            font-weight: 500;
        }
        input[type="text"], input[type="password"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        input:focus {
            border-color: #2a5298;
            outline: none;
        }
        .btn {
            padding: 12px 25px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s;
        }
        .btn-primary {
            background: #2a5298;
            color: white;
            width: 100%;
        }
        .btn-primary:hover {
            background: #1e3c72;
        }
        .btn-danger {
            background: #dc3545;
            color: white;
        }
        .btn-danger:hover {
            background: #c82333;
        }
        .btn-success {
            background: #28a745;
            color: white;
        }
        .btn-success:hover {
            background: #218838;
        }
        .alert {
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .alert-warning {
            background: #fff3cd;
            color: #856404;
            border: 1px solid #ffeeba;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: #f8f9fa;
            color: #1e3c72;
            font-weight: 600;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .badge {
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 12px;
            font-weight: 500;
        }
        .badge-admin {
            background: #ffc107;
            color: #333;
        }
        .badge-user {
            background: #17a2b8;
            color: white;
        }
        .actions {
            display: flex;
            gap: 5px;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 20px;
            border-bottom: 2px solid #eee;
        }
        .logout-btn {
            background: #6c757d;
            color: white;
            text-decoration: none;
            padding: 8px 15px;
            border-radius: 5px;
        }
        .logout-btn:hover {
            background: #5a6268;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-number {
            font-size: 32px;
            font-weight: bold;
        }
        .stat-label {
            font-size: 14px;
            opacity: 0.9;
        }
        .security-info {
            background: #e7f3ff;
            border: 1px solid #b3d9ff;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
            font-size: 13px;
            color: #004085;
        }
    </style>
</head>
<body>
    <div class="container">
        {% if not session.get('logged_in') %}
        <div class="login-box">
            <h1>🔐 Painel Admin</h1>
            <p style="text-align: center; color: #666; margin-bottom: 20px;">Estagiario - Gerenciamento de Usuários</p>
            
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            <form method="POST" action="/admin/login">
                <div class="form-group">
                    <label for="username">Usuário</label>
                    <input type="text" id="username" name="username" required autocomplete="username">
                </div>
                <div class="form-group">
                    <label for="password">Senha</label>
                    <input type="password" id="password" name="password" required autocomplete="current-password">
                </div>
                <button type="submit" class="btn btn-primary">Entrar</button>
            </form>
            <div class="security-info">
                🔒 Conexão segura. Máximo de tentativas excedido será bloqueado temporariamente.
            </div>
        </div>
        {% else %}
        <div class="admin-box">
            <div class="header">
                <h2>👥 Gerenciamento de Usuários</h2>
                <a href="/admin/logout" class="logout-btn">Sair</a>
            </div>
            
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number">{{ users|length }}</div>
                    <div class="stat-label">Total de Usuários</div>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                    <div class="stat-number">{{ admins }}</div>
                    <div class="stat-label">Administradores</div>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                    <div class="stat-number">{{ users|length - admins }}</div>
                    <div class="stat-label">Usuários Comuns</div>
                </div>
            </div>
            
            <h3>➕ Criar Novo Usuário</h3>
            <form method="POST" action="/admin/criar" style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <div style="display: grid; grid-template-columns: 1fr 1fr auto; gap: 15px; align-items: end;">
                    <div class="form-group" style="margin-bottom: 0;">
                        <label for="new_username">Usuário</label>
                        <input type="text" id="new_username" name="username" required>
                    </div>
                    <div class="form-group" style="margin-bottom: 0;">
                        <label for="new_password">Senha</label>
                        <input type="password" id="new_password" name="password" required minlength="8">
                    </div>
                    <button type="submit" class="btn btn-success">Criar Usuário</button>
                </div>
                <div style="margin-top: 15px;">
                    <label>
                        <input type="checkbox" name="is_admin" value="1"> Tornar administrador
                    </label>
                </div>
            </form>
            
            <h3>📋 Lista de Usuários</h3>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Usuário</th>
                        <th>Tipo</th>
                        <th>Criado em</th>
                        <th>Último acesso</th>
                        <th>Ações</th>
                    </tr>
                </thead>
                <tbody>
                    {% for user in users %}
                    <tr>
                        <td>{{ user.id }}</td>
                        <td><strong>{{ user.username }}</strong></td>
                        <td>
                            <span class="badge {% if user.is_admin %}badge-admin{% else %}badge-user{% endif %}">
                                {% if user.is_admin %}Admin{% else %}Usuário{% endif %}
                            </span>
                        </td>
                        <td>{{ user.created_at }}</td>
                        <td>{{ user.last_login or 'Nunca' }}</td>
                        <td class="actions">
                            {% if user.username != 'admin' or admins > 1 %}
                            <form method="POST" action="/admin/deletar" style="display: inline;">
                                <input type="hidden" name="username" value="{{ user.username }}">
                                <button type="submit" class="btn btn-danger" onclick="return confirm('Tem certeza que deseja deletar o usuário {{ user.username }}?')">Deletar</button>
                            </form>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            
            <div class="security-info" style="margin-top: 30px;">
                🔒 <strong>Informações de Segurança:</strong><br>
                • Rate limiting: 100 requisições/minuto por IP<br>
                • Tentativas de login excessivas são bloqueadas<br>
                • Headers de segurança HTTP ativados<br>
                • Conexão HTTPS recomendada em produção
            </div>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""


@app.route('/admin')
@limiter.limit("200 per minute")
def index():
    """Página inicial do painel admin."""
    if not session.get('logged_in'):
        return render_template_string(ADMIN_TEMPLATE)
    
    users = database.listar_usuarios()
    admins = sum(1 for u in users if u['is_admin'])
    return render_template_string(ADMIN_TEMPLATE, users=users, admins=admins)


@app.route('/admin/login', methods=['POST'])
@limiter.limit("10 per minute")  # Rate limit específico para login
def login():
    """Processa o login no painel admin."""
    username = request.form.get('username', '').strip()
    password = request.form.    
    # Log de tentativa de login (sem expor informações sensíveis)
    logger.info(f"Tentativa de login para usuário: {username}")
    
    result = database.verificar_login(username, password)
    
    if result['success'] and result['user']['is_admin']:
        session['logged_in'] = True
        session['username'] = username
        session.permanent = True
        logger.info(f"Login bem-sucedido para: {username}")
        return redirect(url_for('index'))
    else:
        logger.warning(f"Login falhou para: {username}")
        flash('Acesso negado! Somente administradores podem acessar.', 'error')
        return redirect(url_for('index'))


@app.route('/admin/logout')
def logout():
    """Faz logout do painel admin."""
    username = session.get('username', 'unknown')
    session.clear()
    logger.info(f"Logout realizado por: {username}")
    return redirect(url_for('index'))


@app.route('/admin/criar', methods=['POST'])
@limiter.limit("20 per minute")
def criar_usuario():
    """Cria um novo usuário."""
    if not session.get('logged_in'):
        flash('Você precisa estar logado!', 'error')
        return redirect(url_for('index'))
    
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    is_admin = request.form.get('is_admin') == '1'
    
    if not username or not password:
        flash('Usuário e senha são obrigatórios!', 'error')
        return redirect(url_for('index'))
    
    # Validação de senha mínima
    if len(password) < 8:
        flash('Senha deve ter pelo menos 8 caracteres!', 'error')
        return redirect(url_for('index'))
    
    result = database.criar_usuario(username, password, is_admin)
    
    if result['success']:
        logger.info(f"Usuário criado: {username} (admin: {is_admin})")
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(url_for('index'))


@app.route('/admin/deletar', methods=['POST'])
@limiter.limit("20 per minute")
def deletar_usuario():
    """Deleta um usuário."""
    if not session.get('logged_in'):
        flash('Você precisa estar logado!', 'error')
        return redirect(url_for('index'))
    
    username = request.form.get('username', '').strip()
    
    result = database.deletar_usuario(username)
    
    if result['success']:
        logger.info(f"Usuário deletado: {username}")
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(url_for('index'))


# Error handlers
@app.errorhandler(429)
def ratelimit_handler(e):
    """Handler para erros de rate limiting"""
    logger.warning(f"Rate limit excedido para IP: {request.remote_addr}")
    return render_template_string("""
        <!DOCTYPE html>
        <html><head><title>429 - Too Many Requests</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>429 - Too Many Requests</h1>
            <p>Você excedeu o limite de requisições. Tente novamente em alguns minutos.</p>
            <p><a href="/admin">Voltar</a></p>
        </body></html>
    """), 429


@app.errorhandler(500)
def internal_error(e):
    """Handler para erros internos"""
    logger.error(f"Erro interno: {str(e)}")
    return render_template_string("""
        <!DOCTYPE html>
        <html><head><title>500 - Internal Server Error</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>500 - Erro Interno</h1>
            <p>Ocorreu um erro. Tente novamente mais tarde.</p>
        </body></html>
    """), 500


def main():
    """Inicia o servidor Flask."""
    # Inicializa o banco de dados
    database.init_db()
    
    # Verifica modo de produção
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print("\n" + "="*50)
    print("  PAINEL ADMIN - ESTAGIARIO")
    print("="*50)
    print("\n🌐 Acesse: http://localhost:5000/admin")
    print("⚠️  Para sair, pressione Ctrl+C\n")
    
    if not debug_mode:
        print("🔒 Modo de produção ativado")
        print(f"🔑 Rate limit: {RATE_LIMIT}")
    
    # Inicia o servidor
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)


if __name__ == '__main__':
    main()


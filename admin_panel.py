#!/usr/bin/env python3
"""
Painel Admin Web para gerenciamento de usuários.
Acesso: http://localhost:5000/admin

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

# Template HTML do painel admin - DESIGN PROFISSIONAL
ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Estagiario - Ferramenta de Clonagem</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #1e3c72;
            --primary-dark: #2a5298;
            --secondary: #667eea;
            --accent: #764ba2;
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --info: #3b82f6;
            --dark: #1f2937;
            --light: #f3f4f6;
            --white: #ffffff;
            --gray-100: #f3f4f6;
            --gray-200: #e5e7eb;
            --gray-300: #d1d5db;
            --gray-500: #6b7280;
            --gray-700: #374151;
            --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            --shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            --radius: 8px;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #667eea 100%);
            min-height: 100vh;
            padding: 20px;
            color: var(--gray-700);
        }
        .container { max-width: 1000px; margin: 0 auto; }
        
        /* Login Box */
        .login-box {
            background: var(--white);
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
            max-width: 440px;
            margin: 60px auto;
        }
        .login-logo {
            text-align: center;
            margin-bottom: 30px;
        }
        .login-logo h1 {
            font-size: 32px;
            color: var(--primary);
            margin-bottom: 8px;
        }
        .login-logo p {
            color: var(--gray-500);
            font-size: 14px;
        }
        
        /* Cards */
        .card {
            background: var(--white);
            border-radius: 16px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        .card-header {
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: var(--white);
            padding: 24px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .card-header h2 {
            font-size: 20px;
            font-weight: 600;
        }
        .card-body {
            padding: 30px;
        }
        
        /* Form Elements */
        .form-group { margin-bottom: 20px; }
        .form-label {
            display: block;
            font-size: 13px;
            font-weight: 600;
            color: var(--gray-700);
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .form-control {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid var(--gray-200);
            border-radius: var(--radius);
            font-size: 14px;
            transition: all 0.2s;
            background: var(--gray-100);
        }
        .form-control:focus {
            border-color: var(--primary);
            outline: none;
            background: var(--white);
            box-shadow: 0 0 0 3px rgba(30, 60, 114, 0.1);
        }
        .form-hint {
            font-size: 12px;
            color: var(--gray-500);
            margin-top: 6px;
        }
        
        /* Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 12px 24px;
            border: none;
            border-radius: var(--radius);
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            text-decoration: none;
        }
        .btn-primary {
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: var(--white);
            width: 100%;
        }
        .btn-primary:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(30, 60, 114, 0.3);
        }
        .btn-danger {
            background: var(--danger);
            color: var(--white);
            padding: 8px 16px;
            font-size: 13px;
        }
        .btn-danger:hover {
            background: #dc2626;
        }
        .btn-logout {
            background: rgba(255,255,255,0.2);
            color: var(--white);
            padding: 8px 20px;
        }
        .btn-logout:hover {
            background: rgba(255,255,255,0.3);
        }
        
        /* Alerts */
        .alert {
            padding: 16px 20px;
            border-radius: var(--radius);
            margin-bottom: 20px;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .alert-success {
            background: #d1fae5;
            color: #065f46;
            border: 1px solid #a7f3d0;
        }
        .alert-error {
            background: #fee2e2;
            color: #991b1b;
            border: 1px solid #fecaca;
        }
        
        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: linear-gradient(135deg, var(--secondary) 0%, var(--accent) 100%);
            color: var(--white);
            padding: 24px;
            border-radius: var(--radius);
            text-align: center;
        }
        .stat-card.success { background: linear-gradient(135deg, #10b981 0%, #059669 100%); }
        .stat-card.info { background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); }
        .stat-card.warning { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); }
        .stat-number {
            font-size: 36px;
            font-weight: 700;
            line-height: 1;
        }
        .stat-label {
            font-size: 13px;
            opacity: 0.9;
            margin-top: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* Table */
        .table-container {
            overflow-x: auto;
            margin-top: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th {
            background: var(--gray-100);
            color: var(--gray-700);
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            padding: 14px 16px;
            text-align: left;
            border-bottom: 2px solid var(--gray-200);
        }
        td {
            padding: 16px;
            border-bottom: 1px solid var(--gray-200);
            font-size: 14px;
        }
        tr:hover { background: var(--gray-100); }
        
        /* Badge */
        .badge {
            display: inline-flex;
            align-items: center;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-admin {
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            color: white;
        }
        .badge-user {
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white;
        }
        .badge-expired {
            background: var(--danger);
            color: white;
        }
        .badge-active {
            background: var(--success);
            color: white;
        }
        
        /* User Panel (Non-admin) */
        .user-panel {
            text-align: center;
            padding: 40px;
        }
        .user-panel-icon {
            width: 80px;
            height: 80px;
            background: linear-gradient(135deg, var(--secondary) 0%, var(--accent) 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px;
            font-size: 36px;
            color: white;
        }
        
        /* Create User Form */
        .create-user-form {
            background: var(--gray-100);
            padding: 24px;
            border-radius: var(--radius);
            margin-bottom: 30px;
        }
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 16px;
            align-items: end;
        }
        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .checkbox-group input {
            width: 18px;
            height: 18px;
        }
        
        /* Info Box */
        .info-box {
            background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%);
            border: 1px solid #7dd3fc;
            border-radius: var(--radius);
            padding: 16px;
            margin-top: 20px;
            font-size: 13px;
            color: #0369a1;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .stats-grid { grid-template-columns: 1fr; }
            .form-row { grid-template-columns: 1fr; }
            .login-box { margin: 20px; padding: 30px 20px; }
        }
    </style>
</head>
<body>
    <div class="container">
        {% if not session.get('logged_in') %}
        <div class="login-box">
            <div class="login-logo">
                <h1>🔐 Estagiario</h1>
                <p>Ferramenta Profissional de Clonagem de Sites</p>
            </div>
            
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            <form method="POST" action="/admin/login">
                <div class="form-group">
                    <label class="form-label">Usuário</label>
                    <input type="text" name="username" class="form-control" required autocomplete="username" placeholder="Digite seu usuário">
                </div>
                <div class="form-group">
                    <label class="form-label">Senha</label>
                    <input type="password" name="password" class="form-control" required autocomplete="current-password" placeholder="Digite sua senha">
                </div>
                <button type="submit" class="btn btn-primary">Entrar</button>
            </form>
            
            <div class="info-box" style="margin-top: 20px;">
                🔒 Conexão segura. Máximo de tentativas excedido será bloqueado temporariamente.
            </div>
        </div>
        {% else %}
        
        {% if is_admin %}
        <!-- Painel do Admin -->
        <div class="card">
            <div class="card-header">
                <h2>👥 Gerenciamento de Usuários</h2>
                <a href="/admin/logout" class="btn btn-logout">Sair</a>
            </div>
            <div class="card-body">
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="alert alert-{{ category }}">{{ message }}</div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{{ users|length }}</div>
                        <div class="stat-label">Total de Usuários</div>
                    </div>
                    <div class="stat-card success">
                        <div class="stat-number">{{ admins }}</div>
                        <div class="stat-label">Administradores</div>
                    </div>
                    <div class="stat-card info">
                        <div class="stat-number">{{ users|length - admins }}</div>
                        <div class="stat-label">Usuários Comuns</div>
                    </div>
                </div>
                
                <h3 style="margin-bottom: 16px; color: var(--primary);">➕ Criar Novo Usuário</h3>
                <form method="POST" action="/admin/criar" class="create-user-form">
                    <div class="form-row">
                        <div class="form-group" style="margin-bottom: 0;">
                            <label class="form-label">Usuário</label>
                            <input type="text" name="username" class="form-control" required placeholder="Nome de usuário">
                        </div>
                        <div class="form-group" style="margin-bottom: 0;">
                            <label class="form-label">Senha</label>
                            <input type="password" name="password" class="form-control" required minlength="8" placeholder="Mínimo 8 caracteres">
                        </div>
                        <div class="form-group" style="margin-bottom: 0;">
                            <label class="form-label">Expira em (opcional)</label>
                            <input type="date" name="access_expires" class="form-control">
                        </div>
                    </div>
                    <div style="margin-top: 16px; display: flex; justify-content: space-between; align-items: center;">
                        <div class="checkbox-group">
                            <input type="checkbox" id="is_admin" name="is_admin" value="1">
                            <label for="is_admin" style="margin-bottom: 0; font-weight: normal;">Tornar administrador</label>
                        </div>
                        <button type="submit" class="btn btn-primary" style="width: auto;">Criar Usuário</button>
                    </div>
                </form>
                
                <h3 style="margin-bottom: 16px; color: var(--primary);">📋 Lista de Usuários</h3>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Usuário</th>
                                <th>Tipo</th>
                                <th>Criado em</th>
                                <th>Último acesso</th>
                                <th>Expira em</th>
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
                                <td>
                                    {% if user.access_expires %}
                                        <span class="badge {% if user.access_expires < '2024-01-01' %}badge-expired{% else %}badge-active{% endif %}">
                                            {{ user.access_expires }}
                                        </span>
                                    {% else %}
                                        <span style="color: var(--gray-500);">Ilimitado</span>
                                    {% endif %}
                                </td>
                                <td>
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
                </div>
                
                <div class="info-box">
                    🔒 <strong>Informações de Segurança:</strong><br>
                    • Rate limiting: 100 requisições/minuto por IP<br>
                    • Tentativas de login excessivas são bloqueadas<br>
                    • Headers de segurança HTTP ativados<br>
                    • Conexão HTTPS recomendada em produção
                </div>
            </div>
        </div>
        
        {% else %}
        <!-- Painel do Usuário Comum -->
        <div class="card">
            <div class="card-header">
                <h2>🎯 Área do Usuário</h2>
                <a href="/admin/logout" class="btn btn-logout">Sair</a>
            </div>
            <div class="card-body">
                <div class="user-panel">
                    <div class="user-panel-icon">👤</div>
                    <h2 style="color: var(--primary); margin-bottom: 10px;">Bem-vindo, {{ session.get('username') }}!</h2>
                    <p style="color: var(--gray-500); margin-bottom: 30px;">
                        Você tem acesso à ferramenta de clonagem de sites.<br>
                        Use a interface CLI ou desktop para clonar sites.
                    </p>
                    <div style="background: var(--gray-100); padding: 20px; border-radius: var(--radius); text-align: left;">
                        <h4 style="color: var(--primary); margin-bottom: 10px;">📌 Como usar:</h4>
                        <ul style="color: var(--gray-700); font-size: 14px; line-height: 1.8; padding-left: 20px;">
                            <li>Execute o programa Estagiario.exe</li>
                            <li>Faça login com suas credenciais</li>
                            <li>Digite a URL do site que deseja clonar</li>
                            <li>Escolha o local para salvar os arquivos</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
        {% endif %}
        
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
    
    # Verifica se o usuário é admin
    username = session.get('username')
    users = database.listar_usuarios()
    admins = sum(1 for u in users if u['is_admin'])
    
    current_user = next((u for u in users if u['username'] == username), None)
    is_admin = current_user['is_admin'] if current_user else False
    
    return render_template_string(ADMIN_TEMPLATE, users=users, admins=admins, is_admin=is_admin)


@app.route('/admin/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    """Processa o login no painel admin."""
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    logger.info(f"Tentativa de login para usuário: {username}")
    
    result = database.verificar_login(username, password)
    
    if result['success']:
        session['logged_in'] = True
        session['username'] = username
        session.permanent = True
        logger.info(f"Login bem-sucedido para: {username}")
        return redirect(url_for('index'))
    else:
        logger.warning(f"Login falhou para: {username}")
        flash(result.get('message', 'Acesso negado!'), 'error')
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
    
    username_session = session.get('username')
    users = database.listar_usuarios()
    current_user = next((u for u in users if u['username'] == username_session), None)
    
    if not current_user or not current_user['is_admin']:
        flash('Acesso negado! Apenas administradores podem criar usuários.', 'error')
        return redirect(url_for('index'))
    
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    is_admin = request.form.get('is_admin') == '1'
    access_expires = request.form.get('access_expires', '').strip()
    
    if not username or not password:
        flash('Usuário e senha são obrigatórios!', 'error')
        return redirect(url_for('index'))
    
    if len(password) < 8:
        flash('Senha deve ter pelo menos 8 caracteres!', 'error')
        return redirect(url_for('index'))
    
    # Converter string vazia para None
    access_expires = access_expires if access_expires else None
    
    result = database.criar_usuario(username, password, is_admin, access_expires)
    
    if result['success']:
        logger.info(f"Usuário criado: {username} (admin: {is_admin}, expira: {access_expires})")
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
    
    username_session = session.get('username')
    users = database.listar_usuarios()
    current_user = next((u for u in users if u['username'] == username_session), None)
    
    if not current_user or not current_user['is_admin']:
        flash('Acesso negado! Apenas administradores podem deletar usuários.', 'error')
        return redirect(url_for('index'))
    
    username = request.form.get('username', '').strip()
    
    result = database.deletar_usuario(username)
    
    if result['success']:
        logger.info(f"Usuário deletado: {username}")
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(url_for('index'))


@app.errorhandler(429)
def ratelimit_handler(e):
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
    database.init_db()
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print("\n" + "="*50)
    print("  PAINEL ADMIN - ESTAGIARIO")
    print("="*50)
    print("\n🌐 Acesse: http://localhost:5000/admin")
    print("⚠️  Para sair, pressione Ctrl+C\n")
    
    if not debug_mode:
        print("🔒 Modo de produção ativado")
        print(f"🔑 Rate limit: {RATE_LIMIT}")
    
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)


if __name__ == '__main__':
    main()


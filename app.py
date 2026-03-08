#!/usr/bin/env python3
"""
Aplicação web completa com login e redirecionamento para admin.
Deploy: Render.com (grátis)
"""
import os
import sys
import secrets

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import database

# Configurações
SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
RATE_LIMIT = os.environ.get('RATE_LIMIT', '100 per minute')

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Rate Limiter
limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT])
limiter.init_app(app)

# Template de Login
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Estagiario - Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-box {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            width: 100%;
            max-width: 400px;
        }
        h1 { color: #1e3c72; text-align: center; margin-bottom: 10px; }
        .subtitle { text-align: center; color: #666; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; color: #333; font-weight: 500; }
        input {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        input:focus { border-color: #2a5298; outline: none; }
        button {
            width: 100%;
            padding: 12px;
            background: #2a5298;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
        }
        button:hover { background: #1e3c72; }
        .alert {
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>🔐 Estagiario</h1>
        <p class="subtitle">Ferramenta de Clonagem de Sites</p>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <form method="POST">
            <div class="form-group">
                <label>Usuário</label>
                <input type="text" name="username" required>
            </div>
            <div class="form-group">
                <label>Senha</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit">Entrar</button>
        </form>
    </div>
</body>
</html>
"""

# Headers de segurança
@app.after_request
def add_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response


@app.route('/')
@limiter.limit("50 per minute")
def index():
    """Página inicial com login"""
    if session.get('logged_in'):
        return redirect(url_for('admin'))
    return render_template_string(LOGIN_TEMPLATE)


@app.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    """Processa login e redireciona para admin"""
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    
    result = database.verificar_login(username, password)
    
    if result['success']:
        session['logged_in'] = True
        session['username'] = username
        session['is_admin'] = result['user'].get('is_admin', False)
        return redirect(url_for('admin'))
    else:
        flash('Usuário ou senha incorretos!', 'error')
        return redirect(url_for('index'))


@app.route('/admin')
def admin():
    """Painel Admin - redireciona para admin_panel"""
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    
    users = database.listar_usuarios()
    admins = sum(1 for u in users if u['is_admin'])
    
    # Template inline do admin
    ADMIN_PANEL = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Painel Admin - Estagiario</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Segoe UI', sans-serif; background: #f5f5f5; padding: 20px; }
            .container { max-width: 900px; margin: 0 auto; }
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
            .box { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #1e3c72; margin-bottom: 20px; }
            .logout { background: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #f8f9fa; color: #1e3c72; }
            .badge { padding: 5px 10px; border-radius: 15px; font-size: 12px; }
            .badge-admin { background: #ffc107; color: #333; }
            .badge-user { background: #17a2b8; color: white; }
            .form-group { margin-bottom: 15px; }
            input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
            .btn { padding: 10px 20px; background: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer; }
            .alert { padding: 15px; border-radius: 5px; margin-bottom: 20px; }
            .alert-success { background: #d4edda; color: #155724; }
            .alert-error { background: #f8d7da; color: #721c24; }
            .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 30px; }
            .stat-card { background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 20px; border-radius: 8px; text-align: center; }
            .stat-number { font-size: 32px; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>👥 Painel Admin</h1>
                <a href="/logout" class="logout">Sair</a>
            </div>
            
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            <div class="stats">
                <div class="stat-card"><div class="stat-number">{{ users|length }}</div><div>Total Usuários</div></div>
                <div class="stat-card"><div class="stat-number">{{ admins }}</div><div>Administradores</div></div>
                <div class="stat-card"><div class="stat-number">{{ users|length - admins }}</div><div>Usuários</div></div>
            </div>
            
            <div class="box">
                <h3>➕ Criar Usuário</h3>
                <form method="POST" action="/admin/criar" style="margin-top: 15px;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr auto; gap: 10px;">
                        <input type="text" name="username" placeholder="Usuário" required>
                        <input type="password" name="password" placeholder="Senha (mín. 8 caracteres)" required minlength="8">
                        <button type="submit" class="btn">Criar</button>
                    </div>
                    <label style="margin-top: 10px; display: block;">
                        <input type="checkbox" name="is_admin" value="1"> Administrador
                    </label>
                </form>
                
                <table>
                    <thead>
                        <tr><th>ID</th><th>Usuário</th><th>Tipo</th><th>Criado em</th><th>Ações</th></tr>
                    </thead>
                    <tbody>
                        {% for user in users %}
                        <tr>
                            <td>{{ user.id }}</td>
                            <td><strong>{{ user.username }}</strong></td>
                            <td><span class="badge {% if user.is_admin %}badge-admin{% else %}badge-user{% endif %}">
                                {% if user.is_admin %}Admin{% else %}Usuário{% endif %}
                            </span></td>
                            <td>{{ user.created_at }}</td>
                            <td>
                                {% if user.username != 'admin' or admins > 1 %}
                                <form method="POST" action="/admin/deletar" style="display:inline;">
                                    <input type="hidden" name="username" value="{{ user.username }}">
                                    <button type="submit" class="btn" style="background:#dc3545;padding:5px 10px;font-size:12px;" onclick="return confirm('Deletar?')">✕</button>
                                </form>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(ADMIN_PANEL, users=users, admins=admins)


@app.route('/admin/criar', methods=['POST'])
@limiter.limit("20 per minute")
def criar_usuario():
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    is_admin = request.form.get('is_admin') == '1'
    
    if len(password) < 8:
        flash('Senha deve ter pelo menos 8 caracteres!', 'error')
        return redirect(url_for('admin'))
    
    result = database.criar_usuario(username, password, is_admin)
    flash(result['message'], 'success' if result['success'] else 'error')
    return redirect(url_for('admin'))


@app.route('/admin/deletar', methods=['POST'])
@limiter.limit("20 per minute")
def deletar_usuario():
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    
    username = request.form.get('username', '').strip()
    result = database.deletar_usuario(username)
    flash(result['message'], 'success' if result['success'] else 'error')
    return redirect(url_for('admin'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.errorhandler(429)
def ratelimit(e):
    return "<h1>429 - Many Requests</h1><p>Too many requests. Try again later.</p>", 429


if __name__ == '__main__':
    database.init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)


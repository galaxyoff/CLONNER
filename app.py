#!/usr/bin/env python3
"""
Aplicação web - Versão simplificada para deploy
Integração com o painel admin profissional
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template_string, request, redirect, url_for, session, flash
import database

# Inicializa o banco de dados
database.init_db()
database.criar_admin_padrao()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Template de Login Profissional
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Estagiario - Login</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #1e3c72;
            --primary-dark: #2a5298;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #667eea 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .login-box {
            background: white;
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
            width: 100%;
            max-width: 420px;
        }
        .logo {
            text-align: center;
            margin-bottom: 30px;
        }
        .logo h1 {
            font-size: 36px;
            color: var(--primary);
            margin-bottom: 8px;
        }
        .logo p {
            color: #6b7280;
            font-size: 14px;
        }
        .form-group { margin-bottom: 20px; }
        label {
            display: block;
            margin-bottom: 8px;
            color: #374151;
            font-weight: 600;
            font-size: 13px;
        }
        input {
            width: 100%;
            padding: 14px 16px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 14px;
            transition: all 0.2s;
            background: #f9fafb;
        }
        input:focus {
            border-color: var(--primary);
            outline: none;
            background: white;
            box-shadow: 0 0 0 3px rgba(30, 60, 114, 0.1);
        }
        button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 15px;
            font-weight: 600;
            transition: all 0.2s;
        }
        button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(30, 60, 114, 0.3);
        }
        .alert {
            padding: 14px 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        .alert-error {
            background: #fee2e2;
            color: #991b1b;
            border: 1px solid #fecaca;
        }
        .alert-success {
            background: #d1fae5;
            color: #065f46;
            border: 1px solid #a7f3d0;
        }
        .info {
            margin-top: 20px;
            padding: 14px;
            background: #eff6ff;
            border-radius: 8px;
            font-size: 13px;
            color: #1e40af;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="login-box">
        <div class="logo">
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
        <form method="POST" action="/login">
            <div class="form-group">
                <label>Usuário</label>
                <input type="text" name="username" required autocomplete="username" placeholder="Digite seu usuário">
            </div>
            <div class="form-group">
                <label>Senha</label>
                <input type="password" name="password" required autocomplete="current-password" placeholder="Digite sua senha">
            </div>
            <button type="submit">Entrar</button>
        </form>
        <div class="info">
            🔒 Conexão segura. Máximo de tentativas excedido será bloqueado.
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    if session.get('logged_in'):
        return redirect(url_for('admin'))
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    
    result = database.verificar_login(username, password)
    
    if result['success']:
        session['logged_in'] = True
        session['username'] = username
        return redirect(url_for('admin'))
    else:
        flash(result.get('message', 'Usuário ou senha incorretos!'), 'error')
        return redirect(url_for('index'))

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    
    users = database.listar_usuarios()
    admins = sum(1 for u in users if u['is_admin'])
    
    # Verifica se o usuário é admin
    current_username = session.get('username')
    current_user = next((u for u in users if u['username'] == current_username), None)
    is_admin = current_user['is_admin'] if current_user else False
    
    ADMIN_PANEL = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Painel - Estagiario</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --primary: #1e3c72;
                --primary-dark: #2a5298;
            }
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Inter', sans-serif;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container { max-width: 900px; margin: 0 auto; }
            .card {
                background: white;
                border-radius: 16px;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
                overflow: hidden;
            }
            .card-header {
                background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
                color: white;
                padding: 24px 30px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .card-header h1 { font-size: 20px; font-weight: 600; }
            .card-body { padding: 30px; }
            .btn {
                display: inline-flex;
                align-items: center;
                padding: 10px 20px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 600;
                text-decoration: none;
                transition: all 0.2s;
            }
            .btn-logout {
                background: rgba(255,255,255,0.2);
                color: white;
            }
            .btn-logout:hover { background: rgba(255,255,255,0.3); }
            .btn-primary {
                background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
                color: white;
            }
            .btn-danger {
                background: #ef4444;
                color: white;
                padding: 8px 16px;
                font-size: 13px;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 24px;
                border-radius: 12px;
                text-align: center;
            }
            .stat-number { font-size: 36px; font-weight: 700; }
            .stat-label { font-size: 13px; opacity: 0.9; margin-top: 8px; text-transform: uppercase; }
            table { width: 100%; border-collapse: collapse; }
            th {
                background: #f3f4f6;
                padding: 14px 16px;
                text-align: left;
                font-size: 12px;
                text-transform: uppercase;
                color: #6b7280;
                border-bottom: 2px solid #e5e7eb;
            }
            td { padding: 16px; border-bottom: 1px solid #e5e7eb; font-size: 14px; }
            .badge {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
            }
            .badge-admin { background: #f59e0b; color: white; }
            .badge-user { background: #3b82f6; color: white; }
            .form-group { margin-bottom: 20px; }
            .form-row {
                display: grid;
                grid-template-columns: 1fr 1fr auto;
                gap: 16px;
                align-items: end;
            }
            input {
                width: 100%;
                padding: 12px;
                border: 2px solid #e5e7eb;
                border-radius: 8px;
                font-size: 14px;
            }
            input:focus { border-color: var(--primary); outline: none; }
            .alert {
                padding: 14px 16px;
                border-radius: 8px;
                margin-bottom: 20px;
            }
            .alert-success { background: #d1fae5; color: #065f46; }
            .alert-error { background: #fee2e2; color: #991b1b; }
            .info-box {
                background: #eff6ff;
                border: 1px solid #bfdbfe;
                border-radius: 8px;
                padding: 16px;
                margin-top: 20px;
                font-size: 13px;
                color: #1e40af;
            }
            /* User Panel */
            .user-panel { text-align: center; padding: 40px; }
            .user-icon {
                width: 80px;
                height: 80px;
                background: linear-gradient(135deg, #667eea, #764ba2);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 20px;
                font-size: 36px;
            }
            .user-panel h2 { color: var(--primary); margin-bottom: 10px; }
            .user-panel p { color: #6b7280; margin-bottom: 30px; }
            .instructions {
                background: #f3f4f6;
                padding: 20px;
                border-radius: 12px;
                text-align: left;
            }
            .instructions h4 { color: var(--primary); margin-bottom: 12px; }
            .instructions ul { padding-left: 20px; color: #374151; line-height: 1.8; }
        </style>
    </head>
    <body>
        <div class="container">
            {% if is_admin %}
            <div class="card">
                <div class="card-header">
                    <h1>👥 Gerenciamento de Usuários</h1>
                    <a href="/logout" class="btn btn-logout">Sair</a>
                </div>
                <div class="card-body">
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
                            <div class="stat-label">Total</div>
                        </div>
                        <div class="stat-card" style="background: linear-gradient(135deg, #10b981, #059669);">
                            <div class="stat-number">{{ admins }}</div>
                            <div class="stat-label">Admins</div>
                        </div>
                        <div class="stat-card" style="background: linear-gradient(135deg, #3b82f6, #2563eb);">
                            <div class="stat-number">{{ users|length - admins }}</div>
                            <div class="stat-label">Users</div>
                        </div>
                    </div>
                    <h3 style="margin-bottom: 16px; color: var(--primary);">➕ Criar Usuário</h3>
                    <form method="POST" action="/admin/criar" style="background: #f3f4f6; padding: 20px; border-radius: 12px; margin-bottom: 30px;">
                        <div class="form-row">
                            <div class="form-group" style="margin-bottom: 0;">
                                <label>Usuário</label>
                                <input type="text" name="username" required placeholder="Nome">
                            </div>
                            <div class="form-group" style="margin-bottom: 0;">
                                <label>Senha</label>
                                <input type="password" name="password" required minlength="8" placeholder="Mínimo 8 caracteres">
                            </div>
                            <button type="submit" class="btn btn-primary">Criar</button>
                        </div>
                    </form>
                    <h3 style="margin-bottom: 16px; color: var(--primary);">📋 Usuários</h3>
                    <table>
                        <thead><tr><th>ID</th><th>Usuário</th><th>Tipo</th><th>Criado em</th><th>Ações</th></tr></thead>
                        <tbody>
                            {% for user in users %}
                            <tr>
                                <td>{{ user.id }}</td>
                                <td><strong>{{ user.username }}</strong></td>
                                <td><span class="badge {% if user.is_admin %}badge-admin{% else %}badge-user{% endif %}">{% if user.is_admin %}Admin{% else %}User{% endif %}</span></td>
                                <td>{{ user.created_at }}</td>
                                <td>
                                    {% if user.username != 'admin' or admins > 1 %}
                                    <form method="POST" action="/admin/deletar" style="display:inline;">
                                        <input type="hidden" name="username" value="{{ user.username }}">
                                        <button type="submit" class="btn btn-danger" onclick="return confirm('Deletar {{ user.username }}?')">✕</button>
                                    </form>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
            {% else %}
            <div class="card">
                <div class="card-header">
                    <h1>🎯 Área do Usuário</h1>
                    <a href="/logout" class="btn btn-logout">Sair</a>
                </div>
                <div class="card-body">
                    <div class="user-panel">
                        <div class="user-icon">👤</div>
                        <h2>Bem-vindo, {{ session.get('username') }}!</h2>
                        <p>Você tem acesso à ferramenta de clonagem.</p>
                        <div class="instructions">
                            <h4>📌 Como usar:</h4>
                            <ul>
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
        </div>
    </body>
    </html>
    """
    return render_template_string(ADMIN_PANEL, users=users, admins=admins, is_admin=is_admin)

@app.route('/admin/criar', methods=['POST'])
def criar_usuario():
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    
    username_session = session.get('username')
    users = database.listar_usuarios()
    current_user = next((u for u in users if u['username'] == username_session), None)
    
    if not current_user or not current_user['is_admin']:
        flash('Acesso negado!', 'error')
        return redirect(url_for('admin'))
    
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    is_admin = request.form.get('is_admin') == '1'
    result = database.criar_usuario(username, password, is_admin)
    flash(result['message'], 'success' if result['success'] else 'error')
    return redirect(url_for('admin'))

@app.route('/admin/deletar', methods=['POST'])
def deletar_usuario():
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    
    username_session = session.get('username')
    users = database.listar_usuarios()
    current_user = next((u for u in users if u['username'] == username_session), None)
    
    if not current_user or not current_user['is_admin']:
        flash('Acesso negada!', 'error')
        return redirect(url_for('index'))
    
    username = request.form.get('username', '').strip()
    result = database.deletar_usuario(username)
    flash(result['message'], 'success' if result['success'] else 'error')
    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# API para autenticação do cliente/desktop
@app.route('/api/login', methods=['POST'])
def api_login():
    """API para autenticação de clientes/desktop"""
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    
    result = database.verificar_login(username, password)
    
    if result['success']:
        return {
            'success': True,
            'message': 'Login bem-sucedido!',
            'user': {
                'id': result['user']['id'],
                'username': result['user']['username'],
                'is_admin': result['user']['is_admin'],
                'access_expires': result['user'].get('access_expires')
            }
        }
    else:
        return {'success': False, 'message': result['message']}, 401


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)


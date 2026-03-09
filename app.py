#!/usr/bin/env python3
"""
Aplicação web - Versão profissional com interface de clonagem
Integração com o painel admin profissional
"""
import os
import sys
import threading
import time
import shutil
import zipfile
from datetime import datetime
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template_string, request, redirect, url_for, session, flash, jsonify, send_file
from werkzeug.utils import secure_filename
import database

# Inicializa o banco de dados
database.init_db()
database.criar_admin_padrao()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configurações
CLONES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'clones')
os.makedirs(CLONES_DIR, exist_ok=True)

# Armazena tarefas de clonagem em andamento
clone_tasks = {}  # {task_id: {'status': 'running'|'completed'|'error', 'progress': 0, 'message': '', 'output_dir': ''}}

def get_user_clones_dir(username):
    """Retorna o diretório de clones do usuário"""
    user_dir = os.path.join(CLONES_DIR, secure_filename(username))
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

def run_clone_in_background(task_id, url, output_dir, max_pages, workers):
    """Executa a clonagem em uma thread separada"""
    try:
        from estagiario import SiteCloner
        
        clone_tasks[task_id]['status'] = 'running'
        clone_tasks[task_id]['message'] = 'Iniciando clonagem...'
        
        cloner = SiteCloner(url, output_dir, max_pages, workers)
        
        # Sobrescrever o método run para atualizar progresso
        original_run = cloner.run
        
        def custom_run():
            clone_tasks[task_id]['message'] = 'Clonando site...'
            original_run()
            clone_tasks[task_id]['status'] = 'completed'
            clone_tasks[task_id]['message'] = 'Clonagem concluída!'
            clone_tasks[task_id]['progress'] = 100
        
        cloner.run = custom_run
        cloner.run()
        
        if clone_tasks[task_id]['status'] != 'completed':
            clone_tasks[task_id]['status'] = 'completed'
            clone_tasks[task_id]['message'] = 'Clonagem concluída!'
            
    except Exception as e:
        clone_tasks[task_id]['status'] = 'error'
        clone_tasks[task_id]['message'] = f'Erro: {str(e)}'

def create_zip_from_directory(directory, zip_path):
    """Cria um arquivo ZIP de um diretório"""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(directory))
                zipf.write(file_path, arcname)

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
    
    # Data atual para comparação de expiração
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    
    ADMIN_PANEL = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Painel - Estagiario</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
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
            .container { max-width: 1200px; margin: 0 auto; }
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
            .btn-success {
                background: #10b981;
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
            .badge-expired { background: #ef4444; color: white; }
            .badge-active { background: #10b981; color: white; }
            .form-group { margin-bottom: 20px; }
            .form-row {
                display: grid;
                grid-template-columns: 1fr 1fr 1fr auto;
                gap: 16px;
                align-items: end;
            }
            input, select {
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
            
            /* Clone Form */
            .clone-form {
                background: #f3f4f6;
                padding: 24px;
                border-radius: 12px;
                margin-top: 20px;
            }
            .clone-form h3 {
                color: var(--primary);
                margin-bottom: 16px;
            }
            .clone-input-group {
                display: grid;
                grid-template-columns: 2fr 1fr 1fr auto;
                gap: 12px;
                align-items: end;
            }
            .progress-container {
                margin-top: 20px;
                display: none;
            }
            .progress-bar {
                width: 100%;
                height: 8px;
                background: #e5e7eb;
                border-radius: 4px;
                overflow: hidden;
            }
            .progress-fill {
                height: 100%;
                background: linear-gradient(135deg, #667eea, #764ba2);
                width: 0%;
                transition: width 0.3s;
            }
            .progress-text {
                margin-top: 8px;
                font-size: 13px;
                color: #6b7280;
            }
            
            /* Clones History */
            .clones-list {
                margin-top: 30px;
            }
            .clone-item {
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 12px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .clone-item-info h4 {
                color: var(--primary);
                margin-bottom: 4px;
            }
            .clone-item-info p {
                font-size: 13px;
                color: #6b7280;
            }
            .clone-actions {
                display: flex;
                gap: 8px;
            }
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
                            <div class="form-group" style="margin-bottom: 0;">
                                <label>Expira em</label>
                                <input type="date" name="access_expires" placeholder="Sem expiração">
                            </div>
                            <button type="submit" class="btn btn-primary">Criar</button>
                        </div>
                    </form>
                    <h3 style="margin-bottom: 16px; color: var(--primary);">📋 Usuários</h3>
                    <table>
                        <thead><tr><th>ID</th><th>Usuário</th><th>Tipo</th><th>Criado em</th><th>Expira em</th><th>Status</th><th>Ações</th></tr></thead>
                        <tbody>
                            {% for user in users %}
                            <tr>
                                <td>{{ user.id }}</td>
                                <td><strong>{{ user.username }}</strong></td>
                                <td><span class="badge {% if user.is_admin %}badge-admin{% else %}badge-user{% endif %}">{% if user.is_admin %}Admin{% else %}User{% endif %}</span></td>
                                <td>{{ user.created_at }}</td>
                                <td>{{ user.access_expires or 'Nunca' }}</td>
                                <td>
                                    {% if user.access_expires %}
                                        {% if user.access_expires < '""" + today + """' %}
                                        <span class="badge badge-expired">Expirado</span>
                                        {% else %}
                                        <span class="badge badge-active">Ativo</span>
                                        {% endif %}
                                    {% else %}
                                    <span class="badge badge-active">Ativo</span>
                                    {% endif %}
                                </td>
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
            <!-- Painel do Usuário Comum com Interface de Clonagem -->
            <div class="card">
                <div class="card-header">
                    <h1>🕷️ Clonador de Sites - Estagiário</h1>
                    <a href="/logout" class="btn btn-logout">Sair</a>
                </div>
                <div class="card-body">
                    <div class="user-panel" style="padding: 0; text-align: left; margin-bottom: 30px;">
                        <h2>Bem-vindo, {{ session.get('username') }}! 👋</h2>
                        <p>Cole a URL do site que deseja clonar e clique em iniciar.</p>
                    </div>
                    
                    <div class="clone-form">
                        <h3>🚀 Nova Clonagem</h3>
                        <form id="cloneForm">
                            <div class="clone-input-group">
                                <div class="form-group" style="margin-bottom: 0;">
                                    <label>URL do Site</label>
                                    <input type="url" id="cloneUrl" name="url" required placeholder="https://exemplo.com">
                                </div>
                                <div class="form-group" style="margin-bottom: 0;">
                                    <label>Limite de Páginas</label>
                                    <input type="number" id="cloneMax" name="max_pages" value="50" min="1" max="500">
                                </div>
                                <div class="form-group" style="margin-bottom: 0;">
                                    <label>Workers</label>
                                    <select id="cloneWorkers" name="workers">
                                        <option value="2">2</option>
                                        <option value="4" selected>4</option>
                                        <option value="8">8</option>
                                    </select>
                                </div>
                                <button type="submit" class="btn btn-primary" id="cloneBtn">Clonar</button>
                            </div>
                        </form>
                        
                        <div class="progress-container" id="progressContainer">
                            <div class="progress-bar">
                                <div class="progress-fill" id="progressFill"></div>
                            </div>
                            <p class="progress-text" id="progressText">Iniciando...</p>
                        </div>
                    </div>
                    
                    <div class="clones-list">
                        <h3 style="margin-bottom: 16px; color: var(--primary);">📂 Meus Clones</h3>
                        <div id="clonesList">
                            <p style="color: #6b7280; text-align: center; padding: 20px;">Nenhum clone realizado ainda.</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <script>
                let currentTaskId = null;
                let checkInterval = null;
                
                document.getElementById('cloneForm').addEventListener('submit', async function(e) {
                    e.preventDefault();
                    
                    const url = document.getElementById('cloneUrl').value;
                    const maxPages = document.getElementById('cloneMax').value;
                    const workers = document.getElementById('cloneWorkers').value;
                    
                    const btn = document.getElementById('cloneBtn');
                    const progressContainer = document.getElementById('progressContainer');
                    const progressFill = document.getElementById('progressFill');
                    const progressText = document.getElementById('progressText');
                    
                    btn.disabled = true;
                    btn.textContent = 'Clonando...';
                    progressContainer.style.display = 'block';
                    progressFill.style.width = '30%';
                    progressText.textContent = 'Enviando requisição...';
                    
                    try {
                        const response = await fetch('/api/clone/start', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                url: url,
                                max_pages: parseInt(maxPages),
                                workers: parseInt(workers)
                            })
                        });
                        
                        const data = await response.json();
                        
                        if (data.success) {
                            currentTaskId = data.task_id;
                            progressFill.style.width = '50%';
                            progressText.textContent = 'Clonagem em andamento...';
                            
                            // Verificar progresso a cada 2 segundos
                            checkInterval = setInterval(async () => {
                                const statusResponse = await fetch('/api/clone/status/' + currentTaskId);
                                const statusData = await statusResponse.json();
                                
                                if (statusData.status === 'completed') {
                                    clearInterval(checkInterval);
                                    progressFill.style.width = '100%';
                                    progressText.textContent = '✅ Clonagem concluída!';
                                    btn.disabled = false;
                                    btn.textContent = 'Clonar Novamente';
                                    
                                    Swal.fire({
                                        title: 'Sucesso!',
                                        text: 'Site clonado com sucesso!',
                                        icon: 'success',
                                        confirmButtonText: 'Baixar ZIP'
                                    }).then(() => {
                                        window.location.href = '/api/clone/download/' + currentTaskId;
                                    });
                                } else if (statusData.status === 'error') {
                                    clearInterval(checkInterval);
                                    progressFill.style.width = '100%';
                                    progressFill.style.background = '#ef4444';
                                    progressText.textContent = '❌ Erro: ' + statusData.message;
                                    btn.disabled = false;
                                    btn.textContent = 'Tentar Novamente';
                                } else {
                                    progressText.textContent = statusData.message || 'Clonando...';
                                }
                            }, 2000);
                        } else {
                            throw new Error(data.message);
                        }
                    } catch (error) {
                        Swal.fire('Erro', error.message, 'error');
                        btn.disabled = false;
                        btn.textContent = 'Clonar';
                        progressContainer.style.display = 'none';
                    }
                });
            </script>
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
    access_expires = request.form.get('access_expires', '').strip()
    access_expires = access_expires if access_expires else None
    
    result = database.criar_usuario(username, password, is_admin, access_expires)
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


# API de Clonagem
@app.route('/api/clone/start', methods=['POST'])
def clone_start():
    """Inicia uma nova clonagem"""
    # Verificar autenticação
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    data = request.get_json()
    url = data.get('url', '').strip()
    max_pages = data.get('max_pages', 50)
    workers = data.get('workers', 4)
    
    if not url:
        return jsonify({'success': False, 'message': 'URL não fornecida'}), 400
    
    # Adicionar http se não tiver
    if not url.startswith('http'):
        url = 'https://' + url
    
    # Validar URL
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return jsonify({'success': False, 'message': 'URL inválida'}), 400
    except Exception:
        return jsonify({'success': False, 'message': 'URL inválida'}), 400
    
    username = session.get('username')
    
    # Criar diretório de saída
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    domain = urlparse(url).netloc.replace(':', '_').replace('.', '_')
    output_dir = os.path.join(get_user_clones_dir(username), f"{domain}_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    
    # Criar task ID
    task_id = f"{username}_{timestamp}"
    
    # Inicializar task
    clone_tasks[task_id] = {
        'status': 'pending',
        'progress': 0,
        'message': 'Aguardando...',
        'output_dir': output_dir,
        'url': url,
        'username': username
    }
    
    # Executar em background
    thread = threading.Thread(
        target=run_clone_in_background,
        args=(task_id, url, output_dir, max_pages, workers)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': 'Clonagem iniciada',
        'task_id': task_id
    })


@app.route('/api/clone/status/<task_id>', methods=['GET'])
def clone_status(task_id):
    """Verifica o status de uma clonagem"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    if task_id not in clone_tasks:
        return jsonify({'success': False, 'message': 'Task não encontrada'}), 404
    
    task = clone_tasks[task_id]
    
    # Verificar se a task pertence ao usuário
    username = session.get('username')
    if task['username'] != username:
        return jsonify({'success': False, 'message': 'Acesso negado'}), 403
    
    return jsonify({
        'success': True,
        'status': task['status'],
        'progress': task['progress'],
        'message': task['message']
    })


@app.route('/api/clone/download/<task_id>', methods=['GET'])
def clone_download(task_id):
    """Baixa o resultado da clonagem como ZIP"""
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    
    if task_id not in clone_tasks:
        flash('Clone não encontrado', 'error')
        return redirect(url_for('admin'))
    
    task = clone_tasks[task_id]
    
    # Verificar se a task pertence ao usuário
    username = session.get('username')
    if task['username'] != username:
        flash('Acesso negado', 'error')
        return redirect(url_for('admin'))
    
    output_dir = task['output_dir']
    
    if not os.path.exists(output_dir):
        flash('Diretório não encontrado', 'error')
        return redirect(url_for('admin'))
    
    # Criar ZIP
    zip_filename = f"clone_{task['url'].replace('https://', '').replace('http://', '').replace('.', '_')}.zip"
    zip_path = os.path.join(CLONES_DIR, f"{task_id}.zip")
    
    try:
        create_zip_from_directory(output_dir, zip_path)
        return send_file(zip_path, as_attachment=True, download_name=zip_filename)
    except Exception as e:
        flash(f'Erro ao criar ZIP: {str(e)}', 'error')
        return redirect(url_for('admin'))


@app.route('/api/clone/list', methods=['GET'])
def clone_list():
    """Lista os clones do usuário"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    username = session.get('username')
    user_clones_dir = get_user_clones_dir(username)
    
    clones = []
    if os.path.exists(user_clones_dir):
        for item in os.listdir(user_clones_dir):
            item_path = os.path.join(user_clones_dir, item)
            if os.path.isdir(item_path):
                # Verificar se tem arquivos
                files_count = sum(len(files) for _, _, files in os.walk(item_path))
                clones.append({
                    'name': item,
                    'path': item_path,
                    'files_count': files_count
                })
    
    # Ordenar por data (mais recente primeiro)
    clones.sort(key=lambda x: os.path.getmtime(x['path']), reverse=True)
    
    return jsonify({
        'success': True,
        'clones': clones
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)


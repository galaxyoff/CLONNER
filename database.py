"""
Sistema de gerenciamento de usuários com banco de dados SQLite e hashing de senhas.
"""
import sqlite3
import os
import bcrypt
from datetime import datetime

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'users.db')


def init_db():
    """Inicializa o banco de dados com a tabela de usuários."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            last_login TEXT,
            access_expires TEXT DEFAULT NULL
        )
    ''')
    
    # Verificar se a coluna access_expires existe (migração)
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'access_expires' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN access_expires TEXT DEFAULT NULL")
        print("✓ Coluna access_expires adicionada ao banco de dados")
    
    conn.commit()
    conn.close()


def hash_password(password: str) -> str:
    """Hashea uma senha usando bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verifica se a senha corresponde ao hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def criar_usuario(username: str, password: str, is_admin: bool = False, access_expires: str = None) -> dict:
    """
    Cria um novo usuário no banco de dados.
    Retorna dict com 'success' e 'message'.
    
    Args:
        username: Nome de usuário
        password: Senha do usuário
        is_admin: Se é administrador
        access_expires: Data de expiração do acesso (formato: YYYY-MM-DD)
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Verifica se usuário já existe
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            conn.close()
            return {'success': False, 'message': 'Usuário já existe!'}
        
        # Hashea a senha
        password_hash = hash_password(password)
        
        # Insere novo usuário
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            'INSERT INTO users (username, password_hash, is_admin, created_at, access_expires) VALUES (?, ?, ?, ?, ?)',
            (username, password_hash, 1 if is_admin else 0, created_at, access_expires)
        )
        
        conn.commit()
        conn.close()
        
        return {'success': True, 'message': f'Usuário {username} criado com sucesso!'}
    except Exception as e:
        return {'success': False, 'message': f'Erro ao criar usuário: {str(e)}'}


def deletar_usuario(username: str) -> dict:
    """
    Deleta um usuário do banco de dados.
    Não permite deletar o último admin.
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Verifica se usuário existe
        cursor.execute('SELECT id, is_admin FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return {'success': False, 'message': 'Usuário não encontrado!'}
        
        # Verifica se é o último admin
        if user[1] == 1:  # is_admin
            cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1')
            admin_count = cursor.fetchone()[0]
            if admin_count <= 1:
                conn.close()
                return {'success': False, 'message': 'Não é possível deletar o último admin!'}
        
        cursor.execute('DELETE FROM users WHERE username = ?', (username,))
        conn.commit()
        conn.close()
        
        return {'success': True, 'message': f'Usuário {username} deletado com sucesso!'}
    except Exception as e:
        return {'success': False, 'message': f'Erro ao deletar usuário: {str(e)}'}


def verificar_login(username: str, password: str) -> dict:
    """
    Verifica as credenciais do usuário.
    Retorna dict com 'success', 'message', e dados do usuário.
    Verifica também se o acesso está expirado.
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT id, username, password_hash, is_admin, access_expires FROM users WHERE username = ?',
            (username,)
        )
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return {'success': False, 'message': 'Usuário ou senha incorretos!'}
        
        user_id, username, password_hash, is_admin, access_expires = user
        
        if not verify_password(password, password_hash):
            conn.close()
            return {'success': False, 'message': 'Usuário ou senha incorretos!'}
        
        # Verifica se o acesso expirou
        if access_expires:
            expire_date = datetime.strptime(access_expires, '%Y-%m-%d')
            now = datetime.now()
            if expire_date < now:
                conn.close()
                return {'success': False, 'message': f'Acesso expirado em {access_expires}! Entre em contato com o administrador.'}
        
        # Atualiza último login
        cursor.execute(
            'UPDATE users SET last_login = ? WHERE id = ?',
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id)
        )
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': 'Login bem-sucedido!',
            'user': {
                'id': user_id,
                'username': username,
                'is_admin': bool(is_admin),
                'access_expires': access_expires
            }
        }
    except Exception as e:
        return {'success': False, 'message': f'Erro ao verificar login: {str(e)}'}


def listar_usuarios() -> list:
    """Retorna lista de todos os usuários."""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, username, is_admin, created_at, last_login, access_expires FROM users ORDER BY id')
        users = cursor.fetchall()
        conn.close()
        
        return [
            {
                'id': u[0],
                'username': u[1],
                'is_admin': bool(u[2]),
                'created_at': u[3],
                'last_login': u[4],
                'access_expires': u[5]
            }
            for u in users
        ]
    except Exception as e:
        print(f'Erro ao listar usuários: {e}')
        return []


def usuario_existe(username: str) -> bool:
    """Verifica se um usuário existe no banco de dados."""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    except Exception:
        return False


def criar_admin_padrao():
    """Cria o usuário admin padrão se não existir."""
    if not usuario_existe('admin'):
        result = criar_usuario('admin', '24032010Antonio.', is_admin=True)
        if result['success']:
            print("✓ Usuário admin padrão criado!")
        else:
            print(f"✗ Erro ao criar admin: {result['message']}")
    else:
        print("✓ Usuário admin já existe.")


# Inicializa o banco de dados automaticamente ao importar
if __name__ == '__main__':
    init_db()
    criar_admin_padrao()
    print("\nBanco de dados inicializado!")
    print(f"Local: {DATABASE_PATH}")


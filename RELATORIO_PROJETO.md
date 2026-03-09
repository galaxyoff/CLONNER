# Relatório Técnico Completo do Projeto Estagiário

## 1. Visão Geral do Projeto

O **Estagiário** é uma ferramenta profissional de clonagem de sites desenvolvida em Python. O projeto permite que um usuário baixe e faça uma cópia local de websites inteiros, incluindo todas as páginas HTML, recursos estáticos (imagens, CSS, JavaScript, fontes, vídeos) e estrutura de links interna.

O projeto é composto por duas partes principais:
- **Aplicação Web (Backend + Frontend)**: Painel administrativo para gerenciamento de usuários
- **Aplicação Desktop/CLI**: Ferramenta de clonagem de sites

---

## 2. Arquitetura do Sistema

### 2.1 Estrutura de Arquivos

```
clonner/
├── app.py                 # Aplicação Flask principal (web)
├── admin_panel.py         # Painel admin alternativo
├── database.py            # Módulo de banco de dados SQLite
├── estagiario.py          # Programa principal de clonagem (CLI)
├── downloader.py          # Módulo de download de arquivos
├── parser_utils.py        # Utilitários de parsing HTML
├── rewriter.py            # Módulo de reescrita de links
├── requirements.txt       # Dependências Python
├── Dockerfile             # Configuração Docker
├── docker-compose.yml     # Orquestração Docker
├── Estagiario.spec        # Configuração PyInstaller
├── Procfile               # Deploy no Render
├── nginx.conf             # Configuração Nginx
├── runtime.txt            # Versão Python (3.11)
├── output/                # Diretório de saída dos clones
├── build/                 # Arquivos de build PyInstaller
└── tests/                 # Testes unitários
```

### 2.2 Tecnologias Utilizadas

| Categoria | Tecnologia | Versão |
|-----------|------------|--------|
| Linguagem | Python | 3.11 |
| Web Framework | Flask | ≥2.2.0 |
| Parsing HTML | BeautifulSoup4 | ≥4.11.0 |
| Parser XML/HTML | lxml | ≥4.9.0 |
| HTTP Client | requests | ≥2.28.0 |
| Banco de Dados | SQLite | (built-in) |
| Segurança | bcrypt | ≥4.0.0 |
| Rate Limiting | Flask-Limiter | ≥2.0.0 |
| Servidor WSGI | Gunicorn | ≥20.1.0 |
| Empacotamento | PyInstaller | ≥5.0.0 |

---

## 3. Componentes Principais

### 3.1 Módulo de Banco de Dados (`database.py`)

Este módulo gerencia toda a persistência de dados do sistema:

**Funcionalidades:**
- **Criação de banco de dados SQLite**: Tabela `users` com campos:
  - `id`: Identificador único
  - `username`: Nome de usuário (único)
  - `password_hash`: Senha criptografada com bcrypt
  - `is_admin`: Flag de administrador (0/1)
  - `created_at`: Data de criação
  - `last_login`: Último acesso
  - `access_expires`: Data de expiração de acesso

- **Gerenciamento de usuários**:
  - `criar_usuario()`: Cria novo usuário com senha hasheada
  - `deletar_usuario()`: Remove usuário (proteção contra exclusão do último admin)
  - `verificar_login()`: Valida credenciais e verifica expiração
  - `listar_usuarios()`: Retorna lista de todos os usuários
  - `criar_admin_padrao()`: Cria usuário admin inicial

- **Segurança**:
  - Senhas armazenadas com hash bcrypt
  - Verificação de data de expiração de acesso

**Credenciais padrão:**
- Usuário: `admin`
- Senha: `24032010Antonio.`

---

### 3.2 Módulo de Clonagem de Sites (`estagiario.py`)

Este é o núcleo da aplicação de clonagem:

**Classe `SiteCloner`:**

**Construtor:**
```python
SiteCloner(start_url, output_dir="output", max_pages=None, workers=4)
```

**Parâmetros:**
- `start_url`: URL inicial do site a ser clonado
- `output_dir`: Diretório para salvar os arquivos (padrão: "output")
- `max_pages`: Limite máximo de páginas (None = sem limite)
- `workers`: Número de threads paralelas (padrão: 4)

**Métodos principais:**

1. **`_process(url)`**: Processa uma URL individual
   - Baixa o conteúdo da página
   - Se for HTML: extrai links, reescreve URLs, baixa recursos
   - Se for outro tipo: apenas baixa o arquivo

2. **`_download_page_resources(html, base_url)`**: Baixa todos os recursos de uma página
   - Imagens, CSS, JS, fontes, vídeos, áudios
   - Usa ThreadPoolExecutor para downloads paralelos

3. **`run()`**: Executa o processo de clonagem
   - Gerencia fila de URLs a visitar
   - Processa múltiplas páginas em paralelo
   - Respeita robots.txt
   - Gera relatório final

**Funcionalidades adicionais:**
- Login via API para autenticação
- Suporte a argumentos via linha de comando
- Interface interativa com cores ANSI no terminal
- Respeito ao arquivo robots.txt

**Fluxo de execução:**
```
1. Login no servidor (API)
2. Parse da URL inicial
3. Baixar página principal
4. Extrair todos os links da página
5. Para cada link:
   a. Verificar se já foi visitado
   b. Verificar se é do mesmo domínio
   c. Baixar a página/recursos
   d. Extrair novos links
6. Repetir até limite ou sem mais páginas
7. Gerar relatório final
```

---

### 3.3 Módulo de Download (`downloader.py`)

Responsável por baixar arquivos do servidor remoto:

**Funções principais:**

1. **`download_file(session, url, output_dir, verify_ssl=True)`**:
   - Baixa arquivo via HTTP/HTTPS
   - Determina tipo de conteúdo pelo header Content-Type
   - Salva no diretório de saída mantendo estrutura de pastas
   - Trata encoding de caracteres
   - Retorna caminho local do arquivo salvo

2. **`get_file_extension(content_type, url)`**:
   - Mapeia Content-Type para extensão de arquivo
   - Suporta: HTML, CSS, JS, JSON, imagens, vídeos, áudio, fontes, PDF, ZIP

3. **`get_all_resources_from_html(html, base_url, domain)`**:
   - Extrai todos os recursos referenciados em uma página HTML
   - Procura em: src, href, srcset, style inline
   - Filtra por domínio (recursos internos apenas)

---

### 3.4 Módulo de Parsing (`parser_utils.py`)

Extrai links e recursos de páginas HTML:

**Função `extract_links(html, base_url, domain)`**:
Retorna conjunto de links e objeto BeautifulSoup

**Fontes de links detectados:**
1. `<a href="">` - Links de navegação
2. `<script src="">` - Scripts JavaScript
3. `<link href="">` - CSS externo
4. `<img src="">` e `<img srcset="">` - Imagens
5. `<video>`, `<source>`, `<track>` - Vídeos
6. `<audio>`, `<source>` - Áudio
7. `<object data="">`, `<embed src="">` - Objetos
8. `<use href="">` - SVG
9. `<iframe src="">` - Iframes
10. Background images em estilos inline
11. Data attributes (`data-src`, `data-image`, etc.)
12. Meta tags (og:image, twitter:image, etc.)

**Função `get_resource_type(url)`**:
Determina o tipo de recurso pela extensão:
- `html`: Páginas web
- `css`: Estilos
- `js`: JavaScript
- `image`: Imagens (jpg, png, gif, svg, webp, etc.)
- `font`: Fontes (woff, woff2, ttf, otf)
- `video`: Vídeos
- `audio`: Áudio
- `document`: Documentos (PDF, DOC, etc.)

---

### 3.5 Módulo de Reescrita de Links (`rewriter.py`)

Converte URLs absolutas em caminhos relativos locais:

**Função `rewrite_links(soup, output_dir, domain)`**:
Modifica o BeautifulSoup para usar caminhos locais

**Tipos de reescrita:**
1. **Links em tags HTML**: `<a>`, `<img>`, `<script>`, `<link>`, etc.
2. **Srcset**: Múltiplas resoluções de imagens
3. **Estilos inline**: `url()` em atributos style
4. **Tags `<style>`**: CSS incorporado
5. **Data attributes**: `data-src`, `data-image`, etc.
6. **Meta tags**: Open Graph, Twitter Cards
7. **SVG `<use>`**: Referências SVG

**Função `_make_local_path(output_dir, parsed_url)`**:
Converte URL para caminho de arquivo local:
- Substitui `/` por `\ ` no Windows
- Adiciona `index.html` para diretórios
- Inclui query strings nos nomes de arquivo

---

### 3.6 Aplicação Web (`app.py`)

Servidor Flask com interface web:

**Rotas:**

| Rota | Método | Descrição |
|------|--------|-----------|
| `/` | GET | Página de login |
| `/login` | POST | Processa login |
| `/admin` | GET | Painel admin |
| `/admin/criar` | POST | Criar usuário |
| `/admin/deletar` | POST | Deletar usuário |
| `/logout` | GET | Logout |
| `/api/login` | POST | API de autenticação |

**Funcionalidades:**
- Template HTML profissional com design moderno
- Sessões de login
- Flash messages para feedback
- Verificação de permissões admin
- API REST para autenticação de clientes desktop

---

### 3.7 Painel Admin (`admin_panel.py`)

Versão alternativa do painel administrativo:

**Recursos de segurança:**
- Rate limiting (Flask-Limiter)
- Headers de segurança HTTP:
  - X-Content-Type-Options
  - X-Frame-Options
  - X-XSS-Protection
  - Strict-Transport-Security
  - Content-Security-Policy
- Limite de tentativas de login
- ProxyFix para corretamente obter IP do cliente

**Templates HTML:**
- Design profissional responsivo
- Estatísticas de usuários
- Lista de usuários com Badges
- Formulário de criação de usuário
- Verificação de expiração de acesso

---

## 4. Fluxo de Dados

### 4.1 Fluxo de Clonagem

```
┌─────────────────────────────────────────────────────────────────┐
│                     ESTAGIÁRIO CLI                              │
├─────────────────────────────────────────────────────────────────┤
│  1. Login no servidor (API /api/login)                         │
│  2. URL input → SiteCloner(url)                                 │
│  3. _process(url)                                                │
│     ├── GET request → HTTP response                             │
│     ├── extract_links() → links + soup                         │
│     ├── rewrite_links() → URLs relativas                        │
│     ├── _get_file_path() → caminho local                        │
│     └── Salvar HTML modificado                                 │
│  4. _download_page_resources()                                  │
│     ├── get_all_resources_from_html()                          │
│     └── ThreadPool → download_file() em paralelo                │
│  5. Para cada novo link: adicionar à fila                      │
│  6. Repetir até limite ou sem mais páginas                     │
│  7. Relatório final                                             │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Fluxo de Autenticação

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Cliente    │────▶│   app.py     │────▶│  database.py │
│  (CLI/Web)   │     │  (Flask)     │     │   (SQLite)   │
└──────────────┘     └──────────────┘     └──────────────┘
       │                    │                    │
       │ POST /login        │                    │
       │───────────────────▶│                    │
       │                    │ verificar_login()  │
       │                    │───────────────────▶│
       │                    │                    │
       │                    │   Result + Hash    │
       │                    │◀───────────────────│
       │                    │                    │
       │  Sucesso/Falha     │                    │
       │◀───────────────────│                    │
       │                    │                    │
```

---

## 5. Deploy e Distribuição

### 5.1 Docker

**Dockerfile:**
- Base: Python 3.11-slim
- Exposição da porta 5000
- Variáveis de ambiente configuráveis
- Gunicorn como servidor de produção

**docker-compose.yml:**
- Serviço `web` com app Flask
- Configuração de variáveis de ambiente

### 5.2 Render (Cloud)

**Procfile:**
```
web: python app.py
```

**runtime.txt:**
```
python-3.11.0
```

### 5.3 PyInstaller (Desktop)

**Estagiario.spec:**
- Configuração para criar executável standalone
- Inclui todos os recursos
- Gera Estagiario.exe para Windows

---

## 6. Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `SECRET_KEY` | (gerado) | Chave para sessões Flask |
| `PORT` | 5000 | Porta do servidor |
| `ESTAGIARIO_SERVER` | https://clonner-11.onrender.com | Servidor de autenticação |
| `FLASK_DEBUG` | False | Modo debug |
| `RATE_LIMIT` | 100 per minute | Limite de requisições |

---

## 7. Uso da Ferramenta

### 7.1 Via Interface Web (Painel Admin)

1. Acesse `http://localhost:5000/admin`
2. Faça login com credenciais
3. Gerencie usuários (criar/deletar)
4. Veja estatísticas

### 7.2 Via Linha de Comando (CLI)

```bash
# Clone site completo
python estagiario.py https://exemplo.com

# Clone com opções
python estagiario.py https://exemplo.com -o minha_pasta -m 50 -w 8

# Abra painel admin
python estagiario.py --admin

# Ajuda
python estagiario.py --help
```

**Argumentos:**
- `url`: URL do site (obrigatório)
- `-o, --output`: Pasta de saída (padrão: output)
- `-m, --max`: Máximo de páginas (padrão: sem limite)
- `-w, --workers`: Threads simultâneas (padrão: 4)
- `--admin`: Abrir painel admin

### 7.3 Via Executável (Estagiario.exe)

1. Execute Estagiario.exe
2. Digite URL do site
3. Escolha pasta de destino
4. Aguarde clonagem

---

## 8. Considerações de Segurança

### 8.1 Implementadas

✅ Senhas hasheadas com bcrypt  
✅ Rate limiting no painel admin  
✅ Headers de segurança HTTP  
✅ Verificação de expiração de acesso  
✅ Proteção contra deletion do último admin  
✅ Sessões seguras com SECRET_KEY  
✅ Respeito ao robots.txt  

### 8.2 Recomendações Futuras

⚠️ HTTPS em produção  
⚠️ Rate limiting mais agressivo  
⚠️ Logging de auditoria  
⚠️ Backup do banco de dados  
⚠️ Validação de input mais robusta  
⚠️ Rate limiting por usuário (não só por IP)  

---

## 9. Dependências e Requisitos

```
requests>=2.28.0         # HTTP client
beautifulsoup4>=4.11.0  # HTML parsing
lxml>=4.9.0             # XML/HTML parser
flask>=2.2.0            # Web framework
flask-limiter>=2.0.0    # Rate limiting
bcrypt>=4.0.0           # Password hashing
gunicorn>=20.1.0        # WSGI server
pyinstaller>=5.0.0     # Executable builder
werkzeug>=2.2.0        # WSGI utilities
```

---

## 10. Conclusão

O projeto **Estagiário** é uma ferramenta completa de clonagem de sites que combina:
- Uma aplicação web profissional para gerenciamento de usuários
- Uma ferramenta desktop poderosa para clonagem
- Infraestrutura completa para deploy (Docker, Render)
- Medidas de segurança adequadas para uso em produção

O código é bem estruturado, modularizado e segue boas práticas de desenvolvimento Python. A arquitetura permite fácil expansão e manutenção.

---

*Relatório gerado em: 2024*
*Projeto: Estagiário - Ferramenta de Clonagem de Sites*


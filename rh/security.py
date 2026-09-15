import hashlib
import hmac
import secrets
import sqlite3
import time
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from .config import DB_PATH, USERS, ORIGINS, SECURE_COOKIE

router = APIRouter()
COOKIE = 'rh_session'
TTL = 8 * 60 * 60

def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600000).hex()
    return f'pbkdf2_sha256$600000${salt}${digest}'

def verify_password(password, encoded):
    try:
        algorithm, rounds, salt, expected = encoded.split('$')
        if algorithm != 'pbkdf2_sha256': return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), int(rounds)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, AttributeError): return False

def init_security():
    with sqlite3.connect(DB_PATH) as c:
        c.execute('CREATE TABLE IF NOT EXISTS sessoes (token TEXT PRIMARY KEY, usuario TEXT NOT NULL, expira REAL NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS tentativas_login (chave TEXT, instante REAL)')

def session_user(request):
    token = request.cookies.get(COOKIE, '')
    if not token: return None
    with sqlite3.connect(DB_PATH) as c:
        row = c.execute('SELECT usuario FROM sessoes WHERE token=? AND expira>?', (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
    return row[0] if row and row[0] in USERS else None

async def guard(request, call_next):
    if request.method == 'OPTIONS': return await call_next(request)
    if request.url.path.startswith('/api/'):
        if request.method not in ('GET', 'HEAD'):
            origin = request.headers.get('origin')
            if origin and origin not in ORIGINS:
                return JSONResponse({'erro': 'Origem não autorizada.'}, status_code=403)
        if request.url.path not in ('/api/login', '/api/health'):
            user = session_user(request)
            if not user: return JSONResponse({'erro': 'Sessão expirada. Entre novamente.'}, status_code=401)
            request.state.usuario = user
    return await call_next(request)

class LoginData(BaseModel):
    usuario: str = Field(min_length=1, max_length=100)
    senha: str = Field(min_length=1, max_length=200)

@router.post('/api/login')
def login(dados: LoginData, request: Request, response: Response):
    user = dados.usuario.strip().lower()
    key = request.client.host if request.client else 'local'
    now = time.time()
    with sqlite3.connect(DB_PATH) as c:
        c.execute('DELETE FROM tentativas_login WHERE instante<?', (now - 900,))
        if c.execute('SELECT count(*) FROM tentativas_login WHERE chave=?', (key,)).fetchone()[0] >= 10:
            return JSONResponse({'sucesso': False, 'mensagem': 'Muitas tentativas. Aguarde 15 minutos.'}, status_code=429)
        c.execute('INSERT INTO tentativas_login VALUES (?,?)', (key, now))
    if not verify_password(dados.senha, USERS.get(user, '')):
        return JSONResponse({'sucesso': False, 'mensagem': 'Usuário ou senha incorretos.'}, status_code=401)
    token = secrets.token_urlsafe(32)
    with sqlite3.connect(DB_PATH) as c:
        c.execute('DELETE FROM tentativas_login WHERE chave=?', (key,))
        c.execute('DELETE FROM sessoes WHERE expira<?', (now,))
        c.execute('INSERT INTO sessoes VALUES (?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), user, now + TTL))
    response.set_cookie(COOKIE, token, httponly=True, secure=SECURE_COOKIE, samesite='strict', max_age=TTL, path='/api')
    return {'sucesso': True, 'usuario': user}

@router.get('/api/session')
def session(request: Request): return {'usuario': request.state.usuario}

@router.post('/api/logout')
def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE, '')
    with sqlite3.connect(DB_PATH) as c:
        c.execute('DELETE FROM sessoes WHERE token=?', (hashlib.sha256(token.encode()).hexdigest(),))
    response.delete_cookie(COOKIE, path='/api')
    return {'sucesso': True}

@router.get('/api/health')
def health(): return {'status': 'ok'}

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# JSON local evita colocar credenciais em código e preserva caracteres das senhas.
path = Path(os.environ.get('RH_CONFIG', ROOT / 'config.local.json'))
LOCAL = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
DB_PATH = str(Path(os.environ.get('RH_DB_PATH', ROOT / 'banco_rh.db')).resolve())
NOTION_TOKEN = os.environ.get('NOTION_TOKEN', LOCAL.get('notion_token', ''))
USERS = LOCAL.get('users', {})
ORIGINS = [x.strip() for x in os.environ.get('RH_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173').split(',') if x.strip()]
SECURE_COOKIE = os.environ.get('RH_SECURE_COOKIE', 'false').lower() == 'true'
RULES = LOCAL.get('rules', {})

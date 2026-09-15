"""Atualização atômica: só publica o conjunto completo das bases."""
import concurrent.futures
import json
import logging
import sqlite3
import time
from datetime import datetime, timezone
import requests
from .config import DB_PATH, NOTION_TOKEN

def init_sync():
    with sqlite3.connect(DB_PATH) as c:
        c.execute('CREATE TABLE IF NOT EXISTS sync_status (id INTEGER PRIMARY KEY CHECK(id=1), status TEXT, inicio TEXT, fim TEXT, erro TEXT)')
        c.execute("INSERT OR IGNORE INTO sync_status VALUES (1,'idle',NULL,NULL,NULL)")

def status():
    with sqlite3.connect(DB_PATH) as c:
        row = c.execute('SELECT status,inicio,fim,erro FROM sync_status WHERE id=1').fetchone()
        last = c.execute('SELECT MIN(ultima_atualizacao) FROM notion_cache').fetchone()[0]
        count = c.execute('SELECT count(*) FROM notion_cache').fetchone()[0]
    return dict(zip(('status','inicio','fim','erro'), row)) | {'ultima_atualizacao': last, 'tem_dados': count > 0}

def begin():
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as c:
        c.execute('BEGIN IMMEDIATE')
        row = c.execute('SELECT status,inicio FROM sync_status WHERE id=1').fetchone()
        if row[0] == 'running':
            # Recupera uma execução abandonada depois de queda do processo.
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(row[1])).total_seconds()
            if age < 3600: return False
        c.execute("UPDATE sync_status SET status='running',inicio=?,erro=NULL WHERE id=1", (now,))
    return True

def fetch_database(database_id, payload_filtro=None):
    if not NOTION_TOKEN: raise RuntimeError('Token do Notion não configurado.')
    if not database_id: raise RuntimeError('Base do Notion não configurada.')
    headers = {'Authorization': f'Bearer {NOTION_TOKEN}', 'Notion-Version': '2022-06-28'}
    payload = dict(payload_filtro or {})
    items, seen = [], set()
    while True:
        for attempt in range(5):
            response = requests.post(f'https://api.notion.com/v1/databases/{database_id}/query', headers=headers, json=payload, timeout=(10,30))
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == 4: response.raise_for_status()
                try: delay = min(float(response.headers.get('Retry-After', 2 ** attempt)), 30)
                except ValueError: delay = 2 ** attempt
                time.sleep(max(0, delay)); continue
            response.raise_for_status(); break
        data = response.json()
        items.extend(data['results'])
        if not data.get('has_more'): return items
        cursor = data.get('next_cursor')
        if not cursor or cursor in seen: raise RuntimeError('Paginação incompleta do Notion.')
        seen.add(cursor); payload['start_cursor'] = cursor

def run(databases, clear_cache):
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            futures = {name: pool.submit(fetch_database, database) for name,database in databases.items()}
            complete = {name: future.result() for name,future in futures.items()}
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(DB_PATH) as c:
            for name, items in complete.items():
                c.execute('INSERT INTO notion_cache VALUES (?,?,?) ON CONFLICT(tabela_nome) DO UPDATE SET dados_json=excluded.dados_json,ultima_atualizacao=excluded.ultima_atualizacao', (name,json.dumps(items),now))
            c.execute("UPDATE sync_status SET status='success',fim=?,erro=NULL WHERE id=1", (now,))
        clear_cache()
    except Exception:
        logging.exception('Falha na sincronização; último conjunto completo preservado')
        with sqlite3.connect(DB_PATH) as c:
            c.execute("UPDATE sync_status SET status='error',fim=?,erro=? WHERE id=1", (datetime.now(timezone.utc).isoformat(),'Não foi possível concluir a atualização do Notion. Os dados anteriores foram preservados.'))

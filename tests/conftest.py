import os
import json
import tempfile
from pathlib import Path

_temp = tempfile.TemporaryDirectory(prefix='rh-tests-')
os.environ['RH_DB_PATH'] = str(Path(_temp.name)/'test.db')
os.environ['RH_CONFIG'] = str(Path(_temp.name)/'config.json')
Path(os.environ['RH_CONFIG']).write_text(json.dumps({'users':{},'notion_token':'fake'}),encoding='utf-8')

import pytest
from fastapi.testclient import TestClient
from main import app
from rh.config import USERS, DB_PATH
from rh.security import hash_password
import sqlite3

USERS['rh'] = hash_password('senha-teste')

@pytest.fixture
def client():
    with sqlite3.connect(DB_PATH) as c:
        for table in ('sessoes','tentativas_login','historico_folha','folha_versoes','notion_cache'):
            c.execute(f'DELETE FROM {table}')
        c.execute("UPDATE sync_status SET status='idle',inicio=NULL,fim=NULL,erro=NULL")
    with TestClient(app) as client:
        yield client

@pytest.fixture
def logged(client):
    assert client.post('/api/login',json={'usuario':'rh','senha':'senha-teste'}).status_code==200
    return client

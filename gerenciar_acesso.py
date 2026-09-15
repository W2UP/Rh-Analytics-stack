"""Troca local de senha sem ecoar a credencial no terminal."""
import getpass
import json
import sqlite3
from pathlib import Path
from rh.config import ROOT, DB_PATH
from rh.security import hash_password

if __name__ == '__main__':
    path=ROOT/'config.local.json'
    data=json.loads(path.read_text(encoding='utf-8'))
    user=input('Usuário existente: ').strip().lower()
    if user not in data['users']: raise SystemExit('Usuário não encontrado; nenhum acesso foi criado.')
    password=getpass.getpass('Nova senha (mínimo 12 caracteres): ')
    if len(password)<12 or password != getpass.getpass('Repita a nova senha: '): raise SystemExit('Senha curta ou confirmação diferente.')
    data['users'][user]=hash_password(password)
    temp=path.with_suffix('.json.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)
    with sqlite3.connect(DB_PATH) as c: c.execute('DELETE FROM sessoes WHERE usuario=?',(user,))
    print('Senha atualizada e sessões encerradas. Reinicie o backend para carregar a nova configuração.')

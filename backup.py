"""Backup consistente do SQLite. Execute com o mesmo ambiente do servidor."""
import sqlite3
import shutil
from datetime import datetime
from rh.config import ROOT, DB_PATH

if __name__ == '__main__':
    target=ROOT/'backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
    target.mkdir(parents=True,exist_ok=False)
    with sqlite3.connect(f'file:{DB_PATH}?mode=ro',uri=True) as source, sqlite3.connect(target/'banco_rh.db') as destination:
        source.backup(destination)
    if (ROOT/'config.local.json').exists(): shutil.copy2(ROOT/'config.local.json',target/'config.local.json')
    print(f'Backup salvo em {target}. Mantenha esta pasta privada.')

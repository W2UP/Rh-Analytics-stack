"""Execute com seu usuário do Windows. Preserva os arquivos no disco."""
import subprocess
from pathlib import Path

if __name__ == '__main__':
    root=Path(__file__).resolve().parent
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode('utf-8').split('\0')
    private=[p for p in tracked if p and (p.startswith('Base de Dados/') or p.startswith('__pycache__/') or p.endswith(('.db','.pyc')) or p=='config.local.json')]
    if private:subprocess.run(['git','rm','--cached','--',*private],cwd=root,check=True)
    print(f'{len(private)} arquivos deixaram de ser acompanhados. Todos foram preservados no disco. Revise as alterações antes de fazer commit; o histórico antigo permanece.')

"""Fechamentos com versões imutáveis e validação antes de substituir a visão atual."""
import json
import sqlite3
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from .config import DB_PATH

router = APIRouter()

class Lancamento(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    nome: str = Field(min_length=1)
    setor: str = Field(min_length=1)
    salario_base: float = Field(gt=0)
    horas_desconto: str = Field(pattern=r'^\d+:\d{2}$')
    valor_desconto: float = Field(ge=0)
    faltas_dias: float = Field(default=0,ge=0)

class DadosFolha(BaseModel):
    mes: int = Field(ge=1,le=12)
    ano: int = Field(ge=2000,le=2100)
    lancamentos: list[Lancamento] = Field(min_length=1,max_length=20000)

def init_payroll():
    with sqlite3.connect(DB_PATH) as c:
        c.execute('CREATE TABLE IF NOT EXISTS folha_versoes (id INTEGER PRIMARY KEY AUTOINCREMENT,mes INTEGER,ano INTEGER,usuario TEXT,criado_em TEXT,lancamentos TEXT)')

@router.post('/api/salvar_folha')
def save(data: DadosFolha, request: Request):
    rows = [item.model_dump() for item in data.lancamentos]
    names = [r['nome'].strip().casefold() for r in rows]
    if len(set(names)) != len(names): raise HTTPException(422,'Existem nomes duplicados. Resolva os vínculos por matrícula antes do fechamento.')
    if any('(Não achou)' in r['nome'] or int(r['horas_desconto'].split(':')[1])>59 for r in rows): raise HTTPException(422,'Há colaboradores não identificados ou horários inválidos.')
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as c:
        c.execute('BEGIN IMMEDIATE')
        existing = c.execute('SELECT nome_funcionario AS nome,setor,salario_base,horas_desconto,valor_desconto,faltas_dias FROM historico_folha WHERE mes=? AND ano=?',(data.mes,data.ano))
        fields = [d[0] for d in existing.description]
        previous = [dict(zip(fields,row)) for row in existing.fetchall()]
        if previous and not c.execute('SELECT 1 FROM folha_versoes WHERE mes=? AND ano=?',(data.mes,data.ano)).fetchone():
            c.execute('INSERT INTO folha_versoes(mes,ano,usuario,criado_em,lancamentos) VALUES (?,?,?,?,?)',(data.mes,data.ano,'legado',now,json.dumps(previous)))
        version = c.execute('INSERT INTO folha_versoes(mes,ano,usuario,criado_em,lancamentos) VALUES (?,?,?,?,?)',(data.mes,data.ano,request.state.usuario,now,json.dumps(rows))).lastrowid
        c.execute('DELETE FROM historico_folha WHERE mes=? AND ano=?',(data.mes,data.ano))
        c.executemany('INSERT INTO historico_folha(mes,ano,nome_funcionario,setor,salario_base,horas_desconto,valor_desconto,data_lancamento,faltas_dias) VALUES (?,?,?,?,?,?,?,?,?)',[(data.mes,data.ano,r['nome'],r['setor'],r['salario_base'],r['horas_desconto'],r['valor_desconto'],now,r['faltas_dias']) for r in rows])
    return {'sucesso':True,'versao':version,'mensagem':f'{len(rows)} lançamentos salvos. Versão {version}; histórico anterior preservado.'}

@router.get('/api/folha/versoes')
def versions(mes:int,ano:int):
    with sqlite3.connect(DB_PATH) as c:
        c.row_factory=sqlite3.Row
        return [dict(r) for r in c.execute('SELECT id,usuario,criado_em FROM folha_versoes WHERE mes=? AND ano=? ORDER BY id DESC',(mes,ano))]

@router.get('/api/folha/versoes/{version_id}')
def version(version_id:int):
    with sqlite3.connect(DB_PATH) as c:
        row=c.execute('SELECT lancamentos FROM folha_versoes WHERE id=?',(version_id,)).fetchone()
    if not row: raise HTTPException(404,'Versão não encontrada.')
    return json.loads(row[0])

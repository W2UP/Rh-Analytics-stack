import json
import sqlite3
from datetime import date
from unittest.mock import Mock
import pytest
from rh.config import DB_PATH
from rh import sync
from rh.core import salvar_no_banco
from rh.metrics import period, summarize

def prop(kind,data): return {'type':kind,kind:data}
def person(pid,adm,status='Ativo',name='Mesmo Nome',sector='RH'):
    return {'id':pid,'properties':{'Nome':prop('title',[{'plain_text':name}]),'Data de admissão':prop('date',{'start':adm} if adm else None),'Status':prop('select',{'name':status}),'Setor':prop('select',{'name':sector})}}
def departure(pid,dt,sector='RH'):
    return {'id':'exit-'+pid,'properties':{'Funcionário':prop('relation',[{'id':pid}]),'Data de Desligamento':prop('date',{'start':dt}),'Setor':prop('select',{'name':sector})}}

def test_boundaries_and_duplicates():
    assert period(1,2026)==(date(2025,12,25),date(2026,1,24))
    people=[person('1','2025-12-24'),person('2','2025-12-25'),person('3','2026-01-24','Desligado'),person('4','2026-01-25'),person('5',None)]
    out=summarize(people,[departure('3','2026-01-24')],1,2026,today=date(2026,9,1))
    assert out['admissoes']==2
    assert out['funcionarios']==2
    assert out['desligamentos']==1
    assert out['turnover']=='50.0%'
    assert len(out['detalhes']['admissoes'])==2

def test_historical_count_independent_of_current_status():
    out=summarize([person('1','2025-01-01','Desligado')],[departure('1','2026-08-01')],1,2026,today=date(2026,9,1))
    assert out['funcionarios']==1

def test_sector_future_and_missing_denominator():
    people=[person('1','2026-08-25'),person('2','2026-09-20',sector='TI')]
    assert summarize(people,[],9,2026,'RH',date(2026,9,14))['admissoes']==1
    assert summarize(people,[],9,2026,'TI',date(2026,9,14))['admissoes']==0
    assert summarize(people,[],10,2026,'Todos',date(2026,9,14))['turnover']=='N/D'

@pytest.mark.parametrize('method,path',[('get','/api/dashboard/kpis'),('get','/api/sincronizar/status'),('post','/api/sincronizar'),('post','/api/salvar_folha'),('post','/api/rpa_bonus')])
def test_routes_require_session(client,method,path):
    assert getattr(client,method)(path).status_code==401

def test_session_logout_origin(logged):
    assert logged.get('/api/session').json()['usuario']=='rh'
    assert logged.post('/api/logout',headers={'Origin':'https://untrusted.example'}).status_code==403
    assert logged.post('/api/logout').status_code==200
    assert logged.get('/api/session').status_code==401

def test_login_cookie_and_throttle(client):
    r=client.post('/api/login',json={'usuario':'rh','senha':'senha-teste'})
    assert 'HttpOnly' in r.headers['set-cookie'] and 'SameSite=strict' in r.headers['set-cookie']
    for _ in range(10): assert client.post('/api/login',json={'usuario':'rh','senha':'errada'}).status_code==401
    assert client.post('/api/login',json={'usuario':'rh','senha':'errada'}).status_code==429

def test_dashboard_validates_and_matches_card(logged):
    salvar_no_banco('colaboradores',[person('1','2025-12-25')])
    salvar_no_banco('desligamentos',[])
    assert logged.get('/api/dashboard/kpis?mes=13&ano=2026').status_code==422
    r=logged.get('/api/dashboard/kpis?mes=1&ano=2026')
    assert r.status_code==200, r.text
    data=r.json(); assert data['admissoes']==len(data['detalhes']['admissoes'])==1
    assert data['turnover']=='0.0%'
    assert data['graficoTurnover'][0]['turnover']==0

def test_sync_failure_keeps_all_previous_data(client,monkeypatch):
    salvar_no_banco('colaboradores',[{'id':'old'}]);salvar_no_banco('desligamentos',[{'id':'old-exit'}])
    def fetch(db):
        if db=='bad': raise RuntimeError('simulated')
        return [{'id':'new'}]
    monkeypatch.setattr(sync,'fetch_database',fetch)
    assert sync.begin(); assert not sync.begin()
    sync.run({'colaboradores':'good','desligamentos':'bad'},lambda:None)
    with sqlite3.connect(DB_PATH) as c:
        assert json.loads(c.execute("select dados_json from notion_cache where tabela_nome='colaboradores'").fetchone()[0])==[{'id':'old'}]
    assert sync.status()['status']=='error'

def test_sync_success_commits_together(client,monkeypatch):
    monkeypatch.setattr(sync,'fetch_database',lambda db:[{'id':db}])
    sync.begin(); clear=Mock();sync.run({'colaboradores':'new','desligamentos':'new-exit'},clear)
    assert sync.status()['status']=='success';clear.assert_called_once()
    with sqlite3.connect(DB_PATH) as c:
        assert c.execute('SELECT count(DISTINCT ultima_atualizacao) FROM notion_cache').fetchone()[0]==1

def test_pagination_tls_and_retry(monkeypatch):
    first=Mock(status_code=200);first.json.return_value={'results':[{'id':'a'}],'has_more':True,'next_cursor':'next'}
    last=Mock(status_code=200);last.json.return_value={'results':[{'id':'b'}],'has_more':False}
    post=Mock(side_effect=[first,last]);monkeypatch.setattr(sync.requests,'post',post)
    assert len(sync.fetch_database('db'))==2
    assert 'verify' not in post.call_args.kwargs
    assert post.call_args.kwargs['json']['start_cursor']=='next'

def test_payroll_versions_and_invalid_upload(logged):
    item={'nome':'Colaborador Teste','setor':'RH','salario_base':2200,'horas_desconto':'01:00','valor_desconto':10,'faltas_dias':0}
    payload={'mes':1,'ano':2026,'lancamentos':[item]}
    first=logged.post('/api/salvar_folha',json=payload);assert first.status_code==200,first.text
    item['valor_desconto']=20
    second=logged.post('/api/salvar_folha',json=payload);assert second.status_code==200
    versions=logged.get('/api/folha/versoes?mes=1&ano=2026').json();assert len(versions)==2
    assert logged.get('/api/folha/versoes/'+str(first.json()['versao'])).json()[0]['valor_desconto']==10
    payload['lancamentos']=[];assert logged.post('/api/salvar_folha',json=payload).status_code==422
    with sqlite3.connect(DB_PATH) as c: assert c.execute('SELECT valor_desconto FROM historico_folha').fetchone()[0]==20

def test_money_and_safe_names():
    from rh.rules import money, match_name
    assert money('R$ 2.200,50')==2200.5
    assert money('2200.50')==2200.5
    with pytest.raises(ValueError): money('NaN')
    with pytest.raises(ValueError): match_name('ANA SILVA',['ANA SILVA SOUZA','ANA SILVA LIMA'])
    assert match_name('ANA SILVA',['ANA SILVA'])=='ANA SILVA'

@pytest.mark.parametrize('salary,success',[('R$ 2.200,00',True),('',False)])
def test_import_ponto_salary(logged,monkeypatch,salary,success):
    import pandas as pd
    from rh import ponto
    employee=person('1','2025-01-01',name='Pessoa Teste')
    employee['properties']['Salário (R$)']=prop('rich_text',[{'plain_text':salary}])
    salvar_no_banco('colaboradores',[employee])
    dataframe=pd.DataFrame([['Funcionário: 001 Pessoa Teste',None],['Setor: RH',None],['Tot Descontado','01:00']])
    monkeypatch.setattr(ponto.pd,'read_excel',lambda *a,**k:dataframe)
    response=logged.post('/api/processar_ponto',files={'arquivo':('ponto.xls',b'fixture','application/vnd.ms-excel')})
    data=response.json();assert data['sucesso'] is success,data
    if success: assert data['dados'][0]['valor_desconto']==10

def test_expired_session(logged):
    with sqlite3.connect(DB_PATH) as c: c.execute('UPDATE sessoes SET expira=0')
    assert logged.get('/api/dashboard/kpis').status_code==401

def test_notions_partial_page_failure_is_not_success(monkeypatch):
    first=Mock(status_code=200);first.json.return_value={'results':[{'id':'a'}],'has_more':True,'next_cursor':'next'}
    monkeypatch.setattr(sync.requests,'post',Mock(side_effect=[first,RuntimeError('network failed')]))
    with pytest.raises(RuntimeError): sync.fetch_database('db')

def test_point_uses_identifier_for_homonyms():
    from rh.identity import EmployeeIndex
    a=person('1','2025-01-01');b=person('2','2025-01-01')
    a['properties']['Código']=prop('number',1);b['properties']['Código']=prop('number',2)
    index=EmployeeIndex([a,b])
    assert index.find('0002','Mesmo Nome')['id']=='2'
    with pytest.raises(ValueError):index.find('999','Mesmo Nome')

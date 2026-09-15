"""Competências e movimentações; identidade por página do Notion."""
import calendar
import unicodedata
from collections import Counter
from datetime import date, timedelta

def norm(value):
    return unicodedata.normalize('NFKD', str(value)).encode('ascii','ignore').decode().strip().lower()

def value(prop):
    kind = prop.get('type')
    data = prop.get(kind)
    if kind in ('title','rich_text'): return ''.join(x.get('plain_text', x.get('text',{}).get('content','')) for x in data or [])
    if kind in ('select','status'): return (data or {}).get('name','')
    if kind == 'date': return (data or {}).get('start','')
    if kind == 'number': return str(data) if data is not None else ''
    if kind == 'rollup': return next((v for x in (data or {}).get('array',[]) if (v := value(x))), '')
    return ''

def field(item, *names):
    props = {norm(k):v for k,v in item.get('properties',{}).items()}
    for name in names:
        if norm(name) in props: return value(props[norm(name)])
    return ''

def parsed(raw):
    try: return date.fromisoformat(raw[:10])
    except (ValueError,TypeError): return None

def period(month, year):
    end = date(year, month, 24)
    previous = date(year, month, 1) - timedelta(days=1)
    return previous.replace(day=25), end

def person_id(item):
    for key, prop in item.get('properties',{}).items():
        if prop.get('type') == 'relation' and any(x in norm(key) for x in ('funcion','colab')):
            ids = prop.get('relation',[])
            if len(ids)==1: return ids[0]['id']
    return None

def summarize(collaborators, departures, month, year, sector='Todos', today=None):
    today = today or date.today()
    start,end = period(month,year)
    cutoff = min(end,today)
    # Duplicatas de nome permanecem separadas; apenas a mesma página é deduplicada.
    people = {item['id']:item for item in collaborators if item.get('id')}
    warnings = []
    dates = {}
    departures_by_person = {}
    for item in departures:
        dt = parsed(field(item,'Data de Desligamento'))
        pid = person_id(item)
        if pid and dt: departures_by_person.setdefault(pid,[]).append(dt)
        elif dt: warnings.append('Há desligamentos sem vínculo único com o colaborador; o quadro histórico pode estar incompleto.')
    def selected(item): return sector == 'Todos' or norm(field(item,'Setor')) == norm(sector)
    def departure(pid,admission):
        return min((d for d in departures_by_person.get(pid,[]) if admission and d>=admission), default=None)
    for pid,item in people.items():
        adm = parsed(field(item,'Data de admissão'))
        dates[pid] = (adm,departure(pid,adm))
        if not adm and selected(item): warnings.append('Há colaboradores sem data de admissão válida; eles não entram no quadro histórico.')
        if norm(field(item,'Status')) == 'desligado' and dates[pid][1] is None and selected(item):
            warnings.append('Há colaboradores desligados sem data de desligamento vinculada; eles não entram no quadro histórico.')
    def known(pid):
        item = people[pid]; adm,dep = dates[pid]
        return adm is not None and (norm(field(item,'Status')) != 'desligado' or dep is not None)
    def headcount(at):
        return [i for pid,i in people.items() if selected(i) and known(pid) and dates[pid][0]<=at and (dates[pid][1] is None or dates[pid][1]>at)]
    admissions = [i for i in people.values() if selected(i) and (d:=parsed(field(i,'Data de admissão'))) and start<=d<=cutoff]
    def selected_departure(item):
        # O setor registrado no desligamento tem preferência sobre o setor atual.
        actual = field(item,'Setor') or field(people.get(person_id(item),{}),'Setor')
        return sector == 'Todos' or norm(actual)==norm(sector)
    exits = [i for i in departures if selected_departure(i) and (d:=parsed(field(i,'Data de Desligamento'))) and start<=d<=cutoff]
    opening = headcount(start-timedelta(days=1))
    closing = headcount(cutoff) if cutoff>=start else []
    # Mantém a definição existente (saídas / quadro), corrigindo a base temporal.
    turnover = round(len(exits)/len(closing)*100,1) if closing else None
    def detail(item, kind):
        related = people.get(person_id(item),{}) if kind=='desligamentos' else item
        return {'id':item.get('id',''), 'nome':field(related,'Nome') or field(item,'Registro de Desligamento') or 'Sem identificação', 'setor':field(item,'Setor') or field(related,'Setor') or 'Outros', 'data':field(item,'Data de Desligamento') if kind=='desligamentos' else field(item,'Data de admissão')}
    names=Counter(norm(field(i,'Nome')) for i in people.values())
    if any(n and count>1 for n,count in names.items()): warnings.append('Existem nomes repetidos. O quadro e as admissões usam o identificador do Notion; confira os cruzamentos de arquivos por matrícula.')
    if end < today: warnings.append('Quadro reconstruído por admissão e desligamento. O setor usa o cadastro disponível; transferências históricas e vínculos anteriores não registrados não podem ser reconstruídos.')
    if cutoff < end and cutoff >= start: warnings.append(f'Competência em andamento: movimentações apuradas até {cutoff.strftime("%d/%m/%Y")}.')
    if cutoff < start: warnings.append('Competência futura: ainda não há movimentações realizadas neste período.')
    return {'funcionarios':len(closing),'admissoes':len(admissions),'desligamentos':len(exits),'turnover':f'{turnover:.1f}%' if turnover is not None else 'N/D', 'turnover_valor':turnover,'ativos':closing,'admissoes_itens':admissions,'desligamentos_itens':exits,'inicio':start.isoformat(),'fim':end.isoformat(),'avisos':list(dict.fromkeys(warnings)), 'detalhes':{'funcionarios':[detail(i,'funcionarios') for i in closing], 'admissoes':[detail(i,'admissoes') for i in admissions], 'desligamentos':[detail(i,'desligamentos') for i in exits]}, 'base_turnover':{'quadro_inicio':len(opening),'quadro_fim':len(closing),'desligamentos':len(exits),'formula':'Desligamentos ÷ quadro ao final do período × 100'}}

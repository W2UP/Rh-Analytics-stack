from decimal import Decimal, InvalidOperation
from .config import RULES
from .metrics import norm

def money(raw):
    text=str(raw).replace('R$','').replace(' ','').strip()
    if ',' in text: text=text.replace('.','').replace(',','.')
    try:
        amount=Decimal(text)
        if not amount.is_finite(): raise ValueError('Valor monetário inválido.')
        return float(amount)
    except InvalidOperation: raise ValueError('Salário ausente ou inválido. Corrija o cadastro antes do fechamento.')

def excluded_sector(sector):
    return norm(sector) in {norm(s) for s in RULES.get('setores_excluidos',['Uchoa'])}

def match_name(name, candidates):
    """Só vincula nomes completos ou equivalências revisadas na configuração."""
    target=RULES.get('equivalencias_nomes',{}).get(name,name)
    if target in candidates: return target
    if any(target in c or c in target for c in candidates if c and target):
        raise ValueError('Nome abreviado ou divergente. Revise a identificação e configure uma equivalência antes de gerar o arquivo.')
    return None

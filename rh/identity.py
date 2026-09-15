from collections import defaultdict
from .metrics import field, norm

def code(raw):
    text=str(raw).strip()
    if text.endswith('.0'): text=text[:-2]
    return text.lstrip('0') or ('0' if text else '')

class EmployeeIndex:
    """Código interno do SAP primeiro; nome completo somente quando é único."""
    def __init__(self,people):
        self.codes=defaultdict(list);self.names=defaultdict(list)
        for item in people:
            identifier=code(field(item,'Código'))
            if identifier:self.codes[identifier].append(item)
            self.names[norm(field(item,'Nome'))].append(item)

    def find(self,identifier,name):
        matches=self.codes.get(code(identifier),[])
        if len(matches)==1:return matches[0]
        if len(matches)>1:raise ValueError('Código interno duplicado no Notion. Corrija antes de importar o ponto.')
        matches=self.names.get(norm(name),[])
        if len(matches)==1:return matches[0]
        if len(matches)>1:raise ValueError('Há colaboradores com o mesmo nome. Preencha o Código interno no Notion para vinculá-los ao SAP.')
        raise ValueError('Colaborador do ponto não identificado. Confira o Código interno e o nome completo no Notion.')

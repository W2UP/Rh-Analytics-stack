from typing import Optional, List
from datetime import date, datetime
from sqlmodel import Field, SQLModel, Relationship, create_engine

# 1. TABELA MÃE: Colaboradores
class Colaborador(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    cpf: str = Field(unique=True)
    rg: Optional[str] = None
    data_nascimento: Optional[date] = None
    sexo: Optional[str] = None
    raca_cor: Optional[str] = None
    endereco: Optional[str] = None
    telefone: Optional[str] = None
    
    # Dados Profissionais
    matricula_esocial: Optional[str] = None
    codigo_interno: Optional[str] = None
    cbo: Optional[str] = None
    funcao: str
    setor: str
    data_admissao: date
    salario: float
    tipo_contrato: str
    status: str = Field(default="Ativo") # Ativo, Desligado, Férias, Afastado
    observacoes: Optional[str] = None

    # Relacionamentos (Isso conecta as tabelas)
    atestados: List["Atestado"] = Relationship(back_populates="colaborador")
    advertencias: List["Advertencia"] = Relationship(back_populates="colaborador")
    faltas: List["FaltaAtraso"] = Relationship(back_populates="colaborador")
    desligamento: Optional["Desligamento"] = Relationship(back_populates="colaborador")

# 2. TABELA: Atestados
class Atestado(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    colaborador_id: int = Field(foreign_key="colaborador.id") # A Mágica do Relacionamento
    
    data_entrega: date
    data_inicio: date
    quantidade_dias: int
    cid: Optional[str] = None
    medico: Optional[str] = None
    crm: Optional[str] = None
    local_atendimento: Optional[str] = None
    motivo: str
    tipo: str
    abonado: bool = Field(default=True)
    observacoes: Optional[str] = None
    
    colaborador: Colaborador = Relationship(back_populates="atestados")

# 3. TABELA: Advertências e Suspensões
class Advertencia(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    colaborador_id: int = Field(foreign_key="colaborador.id")
    
    tipo: str # Advertência Verbal, Escrita, Suspensão
    data_ocorrencia: date
    data_aplicacao: date
    motivo: str
    descricao_ocorrencia: str
    dias_suspensao: Optional[int] = Field(default=0)
    aplicada_por: str
    assinada: bool = Field(default=False)
    
    colaborador: Colaborador = Relationship(back_populates="advertencias")

# 4. TABELA: Faltas e Atrasos
class FaltaAtraso(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    colaborador_id: int = Field(foreign_key="colaborador.id")
    
    tipo: str # Falta, Atraso, Saída Antecipada
    data: date
    horas_perdidas: Optional[float] = None # Para atrasos fracionados (ex: 1.5 horas)
    dias_perdidos: Optional[int] = None # Para faltas inteiras
    valor_desconto: Optional[float] = None
    abonado: bool = Field(default=False)
    
    colaborador: Colaborador = Relationship(back_populates="faltas")

# 5. TABELA: Desligamentos
class Desligamento(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    colaborador_id: int = Field(foreign_key="colaborador.id", unique=True)
    
    data_desligamento: date
    tipo_desligamento: str # Sem justa causa, Pedido de demissão, etc.
    motivo_desligamento: str
    iniciativa: str # Empregador, Empregado
    entrevista_realizada: bool = Field(default=False)
    responsavel: str
    
    colaborador: Colaborador = Relationship(back_populates="desligamento")

# --- MOTOR DE CONEXÃO COM O BANCO DE DADOS ---
# No futuro, mudaremos de 'sqlite' para 'postgresql'
sqlite_file_name = "rh_analytics.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

if __name__ == "__main__":
    create_db_and_tables()
    print("Banco de dados criado com sucesso! ✔️")
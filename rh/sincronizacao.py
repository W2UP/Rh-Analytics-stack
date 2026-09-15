from fastapi import APIRouter
from .core import BackgroundTasks, CACHE_RELACOES, DATABASES, sync

router = APIRouter()

@router.post("/api/sincronizar")
def endpoint_sincronizar(background_tasks: BackgroundTasks):
    if sync.begin(): background_tasks.add_task(sync.run, DATABASES, CACHE_RELACOES.clear)
    return {"sucesso": True, "mensagem": "Atualização em andamento."}


@router.get("/api/sincronizar/status")
def status_sincronizacao(): return sync.status()


import truststore
truststore.inject_into_ssl()

"""Entrada da aplicação. Execute: python -m uvicorn main:app --host 127.0.0.1 --port 8000."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rh.config import ORIGINS
from rh.core import iniciar_banco_dados
from rh.security import guard, init_security, router as auth_router
from rh.payroll import init_payroll, router as payroll_router
from rh import sync, ponto, planilhas, auditoria, dashboard, sincronizacao

iniciar_banco_dados()
init_security()
init_payroll()
sync.init_sync()

app = FastAPI(title="RH Analytics ERP", docs_url=None, redoc_url=None, openapi_url=None)
app.middleware("http")(guard)
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
for router in (auth_router, payroll_router, ponto.router, planilhas.router, auditoria.router, dashboard.router, sincronizacao.router):
    app.include_router(router)

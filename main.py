from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from datetime import datetime, timedelta 
import calendar 

app = FastAPI(title="RH Analytics API - Notion")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 🛑 SUAS CHAVES DO NOTION
# ==========================================
NOTION_TOKEN = "ntn_b86757525552BOl8M9h0NsNEntm9aZiTiVxCiwkNa8Kdue"

DB_COLABORADORES = "3ba2051d7a6b8005b98af9fab951026d"
DB_DESLIGAMENTOS = "3ab2051d7a6b808bb0d8fe4199cd5ed9"
DB_ATESTADOS = "ec42d14b9f4243a4ae42a4e704396b1c"
DB_ADVERTENCIAS = "3982051d7a6b8012b894f48c52cdab79"
DB_FREQUENCIA = "39d2051d7a6b805cac20cb52b5c0b476"
DB_DESEMPENHO = "14378c804c6643a3864e72d7947c822f"

class LoginData(BaseModel):
    usuario: str
    senha: str

USUARIOS_PERMITIDOS = {"diretoria": "@senha123", "gerencia": "@senha456", "rh": "@rh2026"}

@app.post("/api/login")
def validar_login(dados: LoginData):
    usuario_digitado = dados.usuario.lower()
    if usuario_digitado in USUARIOS_PERMITIDOS and USUARIOS_PERMITIDOS[usuario_digitado] == dados.senha:
        return {"sucesso": True, "usuario": usuario_digitado}
    return {"sucesso": False, "mensagem": "Usuário ou senha incorretos."}

def buscar_itens_notion(database_id, payload_filtro=None):
    if not database_id or database_id.startswith("ID_"): return []
    headers = {"Authorization": f"Bearer {NOTION_TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    itens, tem_mais_paginas, next_cursor = [], True, None
    if payload_filtro is None: payload_filtro = {}
    while tem_mais_paginas:
        if next_cursor: payload_filtro["start_cursor"] = next_cursor
        resp = requests.post(url, headers=headers, json=payload_filtro)
        if resp.status_code == 200:
            dados = resp.json()
            itens.extend(dados["results"])
            tem_mais_paginas = dados.get("has_more")
            next_cursor = dados.get("next_cursor")
        else:
            print(f"Erro no banco {database_id}:", resp.text)
            break
    return itens

def extrair_texto(propriedades, nome_coluna):
    try:
        if nome_coluna in propriedades:
            prop = propriedades[nome_coluna]
            if prop["type"] == "select" and prop.get("select"): return prop["select"]["name"]
            if prop["type"] == "rich_text" and prop.get("rich_text"): return prop["rich_text"][0]["plain_text"]
            if prop["type"] == "rollup" and prop.get("rollup"):
                arr = prop["rollup"].get("array", [])
                if arr and arr[0].get("title"): return arr[0]["title"][0]["plain_text"]
                if arr and arr[0].get("rich_text"): return arr[0]["rich_text"][0]["plain_text"]
                if arr and arr[0].get("select"): return arr[0]["select"]["name"]
    except: pass
    return "Outros / Não Informado"

@app.get("/api/dashboard/kpis")
def obter_kpis_do_notion(mes: int = None, ano: int = None):
    hoje = datetime.now()
    mes_int = mes if mes else hoje.month
    ano_int = ano if ano else hoje.year

    inicio_mes = f"{ano_int}-{mes_int:02d}-01"
    ultimo_dia = calendar.monthrange(ano_int, mes_int)[1]
    fim_mes_str = f"{ano_int}-{mes_int:02d}-{ultimo_dia}"
    ano_atual = str(ano_int)

    ativos_itens = buscar_itens_notion(DB_COLABORADORES, {"filter": {"property": "Status", "select": {"equals": "Ativo"}}})
    total_ativos = len(ativos_itens)
    
    alertas_aniversarios, alertas_contratos = [], []
    for item in ativos_itens:
        props = item.get("properties", {})
        nome = "Desconhecido"
        for k, v in props.items():
            if v.get("type") == "title" and v.get("title"):
                nome = v["title"][0]["plain_text"]
                break
        prop_nasc = props.get("Data de Nascimento") or props.get("Nascimento") or {}
        if prop_nasc.get("type") == "date" and prop_nasc.get("date"):
            try:
                data_nasc_str = prop_nasc["date"]["start"]
                if int(data_nasc_str.split("-")[1]) == mes_int:
                    alertas_aniversarios.append({"nome": nome, "dia": int(data_nasc_str.split("-")[2])})
            except: pass
        prop_admissao = props.get("Data de admissão") or {}
        if prop_admissao.get("type") == "date" and prop_admissao.get("date"):
            try:
                data_admissao = datetime.strptime(prop_admissao["date"]["start"], "%Y-%m-%d")
                venc_45, venc_90 = data_admissao + timedelta(days=45), data_admissao + timedelta(days=90)
                if venc_45.year == ano_int and venc_45.month == mes_int: alertas_contratos.append({"nome": nome, "dia": venc_45.day, "tipo": "45 Dias"})
                if venc_90.year == ano_int and venc_90.month == mes_int: alertas_contratos.append({"nome": nome, "dia": venc_90.day, "tipo": "90 Dias"})
            except: pass
            
    alertas_aniversarios = sorted(alertas_aniversarios, key=lambda x: x["dia"])
    alertas_contratos = sorted(alertas_contratos, key=lambda x: x["dia"])

    admissoes_itens = buscar_itens_notion(DB_COLABORADORES, {"filter": {"and": [{"property": "Data de admissão", "date": {"on_or_after": inicio_mes}}, {"property": "Data de admissão", "date": {"on_or_before": fim_mes_str}}]}})
    desligamentos_itens = buscar_itens_notion(DB_DESLIGAMENTOS, {"filter": {"and": [{"property": "Data de Desligamento", "date": {"on_or_after": inicio_mes}}, {"property": "Data de Desligamento", "date": {"on_or_before": fim_mes_str}}]}})
    atestados_itens = buscar_itens_notion(DB_ATESTADOS, {"filter": {"and": [{"property": "Data de Entrega", "date": {"on_or_after": inicio_mes}}, {"property": "Data de Entrega", "date": {"on_or_before": fim_mes_str}}]}})
    advertencias_itens = buscar_itens_notion(DB_ADVERTENCIAS, {"filter": {"and": [{"property": "Data da Advertência", "date": {"on_or_after": inicio_mes}}, {"property": "Data da Advertência", "date": {"on_or_before": fim_mes_str}}]}})
    avaliacoes_itens = buscar_itens_notion(DB_DESEMPENHO)
    faltas_itens = buscar_itens_notion(DB_FREQUENCIA, {"filter": {"and": [{"property": "Data", "date": {"on_or_after": inicio_mes}}, {"property": "Data", "date": {"on_or_before": fim_mes_str}}]}})
    
    # FALTAS, ATRASOS E RANKING DE FALTAS
    total_faltas_inteiras, total_atrasos, total_perdas_r = 0, 0, 0.0 
    dict_ranking = {}
    for item in faltas_itens:
        props = item.get("properties", {})
        prop_dias = props.get("Dias") or props.get("# Dias") or {}
        dias_descontados = prop_dias.get("number") if prop_dias.get("type") == "number" else 0
        if dias_descontados and dias_descontados > 0: 
            total_faltas_inteiras += 1
            nome_func = extrair_texto(props, "Funcionário")
            if nome_func == "Outros / Não Informado": nome_func = extrair_texto(props, "Nome")
            if nome_func not in dict_ranking: dict_ranking[nome_func] = 0
            dict_ranking[nome_func] += dias_descontados
        else: 
            total_atrasos += 1
            
        prop_valor = props.get("Valor do desconto") or props.get("Valor do Desconto") or props.get("# Valor do desconto") or {}
        if prop_valor.get("type") == "number" and prop_valor.get("number") is not None: total_perdas_r += prop_valor["number"]
        elif prop_valor.get("type") == "formula" and prop_valor.get("formula", {}).get("type") == "number":
            if prop_valor["formula"].get("number") is not None: total_perdas_r += prop_valor["formula"]["number"]

    ranking_faltas = sorted([{"nome": k, "faltas": v} for k, v in dict_ranking.items()], key=lambda x: x["faltas"], reverse=True)[:5]

    # === RANKING DE ATESTADOS, MÉDICOS E CIDs ===
    dict_ranking_atestados = {}
    dict_medicos = {}
    dict_cids = {}

    for item in atestados_itens:
        props = item.get("properties", {})
        
        # 1. Ranking de Funcionários
        nome_func = extrair_texto(props, "Funcionário")
        if nome_func == "Outros / Não Informado": nome_func = extrair_texto(props, "Nome")
        if nome_func not in dict_ranking_atestados: dict_ranking_atestados[nome_func] = 0
        dict_ranking_atestados[nome_func] += 1

        # 2. Ranking de Médicos
        medico = extrair_texto(props, "Médico")
        if medico and medico != "Outros / Não Informado":
            if medico not in dict_medicos: dict_medicos[medico] = 0
            dict_medicos[medico] += 1

        # 3. Ranking de CIDs + Motivo
        cid = extrair_texto(props, "CID")
        motivo = extrair_texto(props, "Motivo")
        if cid and cid != "Outros / Não Informado":
            # Junta o CID com a Doença se ela existir
            label_cid = f"{cid} - {motivo}" if motivo != "Outros / Não Informado" else cid
            if label_cid not in dict_cids: dict_cids[label_cid] = 0
            dict_cids[label_cid] += 1
    
    ranking_atestados = sorted([{"nome": k, "atestados": v} for k, v in dict_ranking_atestados.items()], key=lambda x: x["atestados"], reverse=True)[:5]
    ranking_medicos = sorted([{"nome": k, "quantidade": v} for k, v in dict_medicos.items()], key=lambda x: x["quantidade"], reverse=True)[:7] # Top 7 Médicos
    ranking_cids = sorted([{"nome": k, "quantidade": v} for k, v in dict_cids.items()], key=lambda x: x["quantidade"], reverse=True)[:10] # Top 10 CIDs

    # MOTIVOS DE ADVERTÊNCIA
    dict_adv = {}
    for item in advertencias_itens:
        motivo = extrair_texto(item.get("properties", {}), "Motivo")
        if motivo == "Outros / Não Informado": motivo = extrair_texto(item.get("properties", {}), "Tipo")
        if motivo not in dict_adv: dict_adv[motivo] = 0
        dict_adv[motivo] += 1
    grafico_advertencias = [{"name": k, "value": v} for k, v in dict_adv.items()]

    # GRÁFICO RADAR DESEMPENHO
    competencias = ["Comunicação", "Produtividade", "Trabalho em Equipe", "Proatividade", "Pontualidade"]
    radar_somas = {c: 0 for c in competencias}
    radar_cont = {c: 0 for c in competencias}
    for item in avaliacoes_itens:
        props = item.get("properties", {})
        for c in competencias:
            prop = props.get(c, {})
            if prop.get("type") == "number" and prop.get("number") is not None:
                radar_somas[c] += prop.get("number")
                radar_cont[c] += 1
    grafico_radar = []
    for c in competencias:
        media = (radar_somas[c] / radar_cont[c]) if radar_cont[c] > 0 else 4.0 
        grafico_radar.append({"subject": c, "A": media, "fullMark": 5})

    # GRAFICOS RESTANTES
    dict_setores = {}
    for item in atestados_itens:
        setor = extrair_texto(item.get("properties", {}), "Setor")
        if setor not in dict_setores: dict_setores[setor] = {"setor": setor, "atestados": 0, "faltas": 0}
        dict_setores[setor]["atestados"] += 1
    for item in faltas_itens:
        setor = extrair_texto(item.get("properties", {}), "Setor")
        if setor not in dict_setores: dict_setores[setor] = {"setor": setor, "atestados": 0, "faltas": 0}
        dict_setores[setor]["faltas"] += 1
    grafico_setores = list(dict_setores.values())

    desligamentos_ano = buscar_itens_notion(DB_DESLIGAMENTOS, {"filter": {"property": "Data de Desligamento", "date": {"on_or_after": f"{ano_atual}-01-01", "on_or_before": f"{ano_atual}-12-31"}}})
    meses_nomes, contagem_meses, dict_motivos = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"], {}, {}
    for m in meses_nomes: contagem_meses[m] = 0
    for item in desligamentos_ano:
        props = item.get("properties", {})
        prop_data = props.get("Data de Desligamento", {})
        if prop_data.get("type") == "date" and prop_data.get("date"):
            mes_idx = int(prop_data["date"]["start"].split("-")[1]) - 1
            contagem_meses[meses_nomes[mes_idx]] += 1
        motivo = extrair_texto(props, "Motivo de Desligamento")
        if motivo not in dict_motivos: dict_motivos[motivo] = 0
        dict_motivos[motivo] += 1
        
    grafico_turnover = [{"mes": mes, "turnover": round((contagem_meses[mes] / total_ativos) * 100, 1) if total_ativos > 0 else 0} for mes in meses_nomes]
    grafico_motivos = [{"name": k, "value": v} for k, v in dict_motivos.items()]

    dict_headcount = {}
    for item in ativos_itens:
        setor = extrair_texto(item.get("properties", {}), "Setor")
        if setor not in dict_headcount: dict_headcount[setor] = 0
        dict_headcount[setor] += 1
    grafico_headcount = sorted([{"setor": k, "quantidade": v} for k, v in dict_headcount.items()], key=lambda x: x["quantidade"], reverse=True)
    turnover_atual = f"{(len(desligamentos_itens) / total_ativos) * 100:.1f}%" if total_ativos > 0 else "0.0%"

    return {
        "funcionarios": total_ativos, "admissoes": len(admissoes_itens), "desligamentos": len(desligamentos_itens), "turnover": turnover_atual,     
        "atestados": len(atestados_itens), "advertencias": len(advertencias_itens), "faltas": total_faltas_inteiras, "atrasos": total_atrasos,
        "custo_absenteismo": total_perdas_r, "avaliacoes": len(avaliacoes_itens),
        "graficoSetores": grafico_setores, "graficoTurnover": grafico_turnover, "graficoMotivos": grafico_motivos, "graficoHeadcount": grafico_headcount,
        "alertasAniversarios": alertas_aniversarios, "alertasContratos": alertas_contratos,
        "graficoAdvertencias": grafico_advertencias, "rankingFaltas": ranking_faltas, 
        "rankingAtestados": ranking_atestados, 
        "rankingMedicos": ranking_medicos, # <--- ENVIANDO MÉDICOS PRO FRONTEND
        "rankingCids": ranking_cids,       # <--- ENVIANDO CIDs PRO FRONTEND
        "graficoRadar": grafico_radar
    }
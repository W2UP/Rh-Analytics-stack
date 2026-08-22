from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from datetime import datetime, timedelta 
import calendar 
import urllib3
import concurrent.futures
import time 

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = FastAPI(title="RH Analytics API - Notion")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        try:
            resp = requests.post(url, headers=headers, json=payload_filtro, verify=False, timeout=30)
            if resp.status_code == 200:
                dados = resp.json()
                itens.extend(dados["results"])
                tem_mais_paginas = dados.get("has_more")
                next_cursor = dados.get("next_cursor")
            elif resp.status_code == 429: 
                time.sleep(1.5) 
                continue
            else:
                break
        except Exception:
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

    f_ativos = {"filter": {"property": "Status", "select": {"equals": "Ativo"}}}
    f_admissoes = {"filter": {"and": [{"property": "Data de admissão", "date": {"on_or_after": inicio_mes}}, {"property": "Data de admissão", "date": {"on_or_before": fim_mes_str}}]}}
    f_deslig_mes = {"filter": {"and": [{"property": "Data de Desligamento", "date": {"on_or_after": inicio_mes}}, {"property": "Data de Desligamento", "date": {"on_or_before": fim_mes_str}}]}}
    f_atestados = {"filter": {"and": [{"property": "Data de Entrega", "date": {"on_or_after": inicio_mes}}, {"property": "Data de Entrega", "date": {"on_or_before": fim_mes_str}}]}}
    f_adv = {"filter": {"and": [{"property": "Data da Advertência", "date": {"on_or_after": inicio_mes}}, {"property": "Data da Advertência", "date": {"on_or_before": fim_mes_str}}]}}
    f_freq = {"filter": {"and": [{"property": "Data", "date": {"on_or_after": inicio_mes}}, {"property": "Data", "date": {"on_or_before": fim_mes_str}}]}}
    f_deslig_ano = {"filter": {"property": "Data de Desligamento", "date": {"on_or_after": f"{ano_atual}-01-01", "on_or_before": f"{ano_atual}-12-31"}}}

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        fut_ativos = executor.submit(buscar_itens_notion, DB_COLABORADORES, f_ativos)
        fut_admissoes = executor.submit(buscar_itens_notion, DB_COLABORADORES, f_admissoes)
        fut_deslig_mes = executor.submit(buscar_itens_notion, DB_DESLIGAMENTOS, f_deslig_mes)
        fut_atestados = executor.submit(buscar_itens_notion, DB_ATESTADOS, f_atestados)
        fut_adv = executor.submit(buscar_itens_notion, DB_ADVERTENCIAS, f_adv)
        fut_freq = executor.submit(buscar_itens_notion, DB_FREQUENCIA, f_freq)
        fut_aval = executor.submit(buscar_itens_notion, DB_DESEMPENHO, None)
        fut_deslig_ano = executor.submit(buscar_itens_notion, DB_DESLIGAMENTOS, f_deslig_ano)

        ativos_itens = fut_ativos.result()
        admissoes_itens = fut_admissoes.result()
        desligamentos_itens = fut_deslig_mes.result()
        atestados_itens = fut_atestados.result()
        advertencias_itens = fut_adv.result()
        faltas_itens = fut_freq.result()
        avaliacoes_itens = fut_aval.result()
        desligamentos_ano = fut_deslig_ano.result()

    total_ativos = len(ativos_itens)
    
    dict_perfis = {}
    
    def get_nome_correto(props):
        nome = extrair_texto(props, "Funcionário")
        if nome == "Outros / Não Informado": nome = extrair_texto(props, "Nome")
        if nome == "Outros / Não Informado":
            for k, v in props.items():
                if v.get("type") == "title" and v.get("title"):
                    return v["title"][0]["plain_text"]
        return nome

    def iniciar_perfil(nome):
        if nome not in dict_perfis:
            dict_perfis[nome] = {
                "cargo": "-", "setor": "-", "tempo_casa": "-", 
                "historico_atestados": [], "historico_advertencias": [],
                "faltas_dias": 0, "atrasos": 0, "nota_desempenho": 0.0, "qtd_aval": 0
            }

    # 1. Base Colaboradores (Férias e Alertas)
    alertas_aniversarios, alertas_contratos, alertas_ferias = [], [], []
    for item in ativos_itens:
        props = item.get("properties", {})
        nome = get_nome_correto(props)
        iniciar_perfil(nome)
        
        dict_perfis[nome]["cargo"] = extrair_texto(props, "Cargo")
        dict_perfis[nome]["setor"] = extrair_texto(props, "Setor")
        
        prop_admissao = props.get("Data de admissão") or {}
        if prop_admissao.get("type") == "date" and prop_admissao.get("date"):
            try:
                adm_str = prop_admissao["date"]["start"]
                data_admissao = datetime.strptime(adm_str, "%Y-%m-%d")
                diff = hoje - data_admissao
                anos, meses = diff.days // 365, (diff.days % 365) // 30
                dict_perfis[nome]["tempo_casa"] = f"{anos} ano(s) e {meses} mês(es)" if anos > 0 else f"{meses} mês(es)"
                
                # --- SPRINT 13: CÁLCULO DE PASSIVO DE FÉRIAS ---
                # A cada 365 dias, o funcionário tem 1 período aquisitivo.
                # Ele tem mais 365 dias (período concessivo) para tirar, senão dobra.
                if diff.days >= 365:
                    dias_para_dobrar = (365 * 2) - diff.days
                    if dias_para_dobrar <= 120 and dias_para_dobrar > -365: # Mostra quem vence em até 4 meses
                        alertas_ferias.append({
                            "nome": nome, 
                            "dias_restantes": dias_para_dobrar, 
                            "setor": dict_perfis[nome]["setor"]
                        })
                # -----------------------------------------------

                venc_45, venc_90 = data_admissao + timedelta(days=45), data_admissao + timedelta(days=90)
                if venc_45.year == ano_int and venc_45.month == mes_int: alertas_contratos.append({"nome": nome, "dia": venc_45.day, "tipo": "45 Dias"})
                if venc_90.year == ano_int and venc_90.month == mes_int: alertas_contratos.append({"nome": nome, "dia": venc_90.day, "tipo": "90 Dias"})
            except: pass
            
        prop_nasc = props.get("Data de Nascimento") or props.get("Nascimento") or {}
        if prop_nasc.get("type") == "date" and prop_nasc.get("date"):
            try:
                data_nasc_str = prop_nasc["date"]["start"]
                if int(data_nasc_str.split("-")[1]) == mes_int:
                    alertas_aniversarios.append({"nome": nome, "dia": int(data_nasc_str.split("-")[2])})
            except: pass

    alertas_aniversarios = sorted(alertas_aniversarios, key=lambda x: x["dia"])
    alertas_contratos = sorted(alertas_contratos, key=lambda x: x["dia"])
    alertas_ferias = sorted(alertas_ferias, key=lambda x: x["dias_restantes"])

    # 2. Frequência (Faltas, Atrasos e HORAS EXTRAS)
    total_faltas_inteiras, total_atrasos, total_perdas_r, total_horas_extras = 0, 0, 0.0, 0.0
    dict_ranking = {}
    dict_he_setor = {} # Ranking de horas extras por setor

    for item in faltas_itens:
        props = item.get("properties", {})
        nome = get_nome_correto(props)
        setor = extrair_texto(props, "Setor")
        iniciar_perfil(nome)
        
        # Faltas e Atrasos
        prop_dias = props.get("Dias") or props.get("# Dias") or {}
        dias_descontados = prop_dias.get("number") if prop_dias.get("type") == "number" else 0
        if dias_descontados and dias_descontados > 0: 
            total_faltas_inteiras += 1
            dict_perfis[nome]["faltas_dias"] += dias_descontados
            dict_ranking[nome] = dict_ranking.get(nome, 0) + dias_descontados
        else: 
            total_atrasos += 1
            dict_perfis[nome]["atrasos"] += 1
            
        prop_valor = props.get("Valor do desconto") or props.get("Valor do Desconto") or props.get("# Valor do desconto") or {}
        if prop_valor.get("type") == "number" and prop_valor.get("number") is not None: total_perdas_r += prop_valor["number"]
        elif prop_valor.get("type") == "formula" and prop_valor.get("formula", {}).get("type") == "number":
            if prop_valor["formula"].get("number") is not None: total_perdas_r += prop_valor["formula"]["number"]

        # --- SPRINT 13: BUSCA DE HORAS EXTRAS NA TABELA DE FREQUÊNCIA ---
        prop_he = props.get("Horas Extras") or props.get("HE") or props.get("Valor HE") or {}
        qtd_he = prop_he.get("number") if prop_he.get("type") == "number" else 0
        if qtd_he and qtd_he > 0:
            total_horas_extras += qtd_he
            if setor not in dict_he_setor: dict_he_setor[setor] = 0
            dict_he_setor[setor] += qtd_he
        # -----------------------------------------------------------------

    ranking_faltas = sorted([{"nome": k, "faltas": v} for k, v in dict_ranking.items()], key=lambda x: x["faltas"], reverse=True)[:5]
    grafico_he = [{"setor": k, "horas": v} for k, v in dict_he_setor.items()]
    grafico_he = sorted(grafico_he, key=lambda x: x["horas"], reverse=True)

    # 3. Atestados
    dict_ranking_atestados, dict_medicos, dict_cids = {}, {}, {}
    for item in atestados_itens:
        props = item.get("properties", {})
        nome = get_nome_correto(props)
        iniciar_perfil(nome)
        dict_ranking_atestados[nome] = dict_ranking_atestados.get(nome, 0) + 1

        medico = extrair_texto(props, "Médico")
        if medico and medico != "Outros / Não Informado": dict_medicos[medico] = dict_medicos.get(medico, 0) + 1

        cid = extrair_texto(props, "CID")
        motivo = extrair_texto(props, "Motivo")
        
        prop_data = props.get("Data de Entrega", {})
        data_str = prop_data.get("date", {}).get("start", "-") if prop_data.get("type") == "date" and prop_data.get("date") else "-"
        
        if cid and cid != "Outros / Não Informado":
            label_cid = f"{cid} - {motivo}" if motivo != "Outros / Não Informado" else cid
            dict_cids[label_cid] = dict_cids.get(label_cid, 0) + 1
            dict_perfis[nome]["historico_atestados"].append({"data": data_str, "motivo": label_cid})
        else:
            dict_perfis[nome]["historico_atestados"].append({"data": data_str, "motivo": motivo})
    
    ranking_atestados = sorted([{"nome": k, "atestados": v} for k, v in dict_ranking_atestados.items()], key=lambda x: x["atestados"], reverse=True)[:5]
    ranking_medicos = sorted([{"nome": k, "quantidade": v} for k, v in dict_medicos.items()], key=lambda x: x["quantidade"], reverse=True)[:7]
    ranking_cids = sorted([{"nome": k, "quantidade": v} for k, v in dict_cids.items()], key=lambda x: x["quantidade"], reverse=True)[:10]

    # 4. Advertências
    dict_adv = {}
    for item in advertencias_itens:
        props = item.get("properties", {})
        nome = get_nome_correto(props)
        iniciar_perfil(nome)
        
        motivo = extrair_texto(props, "Motivo")
        if motivo == "Outros / Não Informado": motivo = extrair_texto(props, "Tipo")
        dict_adv[motivo] = dict_adv.get(motivo, 0) + 1
        
        prop_data = props.get("Data da Advertência", {})
        data_str = prop_data.get("date", {}).get("start", "-") if prop_data.get("type") == "date" and prop_data.get("date") else "-"
        
        dict_perfis[nome]["historico_advertencias"].append({"data": data_str, "motivo": motivo})
        
    grafico_advertencias = [{"name": k, "value": v} for k, v in dict_adv.items()]

    # 5. Desempenho e Competências
    competencias = ["Comunicação", "Produtividade", "Trabalho em Equipe", "Proatividade", "Pontualidade"]
    radar_somas, radar_cont = {c: 0 for c in competencias}, {c: 0 for c in competencias}
    for item in avaliacoes_itens:
        props = item.get("properties", {})
        nome = get_nome_correto(props)
        iniciar_perfil(nome)
        
        soma_func, qtd_func = 0, 0
        for c in competencias:
            prop = props.get(c, {})
            if prop.get("type") == "number" and prop.get("number") is not None:
                radar_somas[c] += prop.get("number")
                radar_cont[c] += 1
                soma_func += prop.get("number")
                qtd_func += 1
                
        if qtd_func > 0:
            media_func = soma_func / qtd_func
            curr_nota = dict_perfis[nome]["nota_desempenho"]
            curr_qtd = dict_perfis[nome]["qtd_aval"]
            dict_perfis[nome]["nota_desempenho"] = ((curr_nota * curr_qtd) + media_func) / (curr_qtd + 1)
            dict_perfis[nome]["qtd_aval"] += 1
            
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
        "rankingAtestados": ranking_atestados, "rankingMedicos": ranking_medicos, "rankingCids": ranking_cids,       
        "graficoRadar": grafico_radar, "perfis360": dict_perfis,
        
        # DADOS SPRINT 13 (FINANCEIRO)
        "alertasFerias": alertas_ferias,
        "totalHorasExtras": total_horas_extras,
        "graficoHorasExtras": grafico_he
    }
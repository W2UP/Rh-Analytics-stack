from fastapi import FastAPI, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from datetime import datetime, timedelta 
import calendar 
import urllib3
import concurrent.futures
import time 
import sqlite3
import json
import pandas as pd
import unicodedata
import io

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = FastAPI(title="RH Analytics ERP - Folha Edition")

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
DB_ARMARIOS = "3872051d7a6b80c2b69ceb5e4db649cb"

DB_PATH = "banco_rh.db"

# ==========================================
# 1. MOTOR DO BANCO DE DADOS LOCAL
# ==========================================
def iniciar_banco_dados():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notion_cache (
            tabela_nome TEXT PRIMARY KEY,
            dados_json TEXT,
            ultima_atualizacao TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

iniciar_banco_dados()

def salvar_no_banco(tabela_nome, dados_lista):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    json_str = json.dumps(dados_lista)
    agora = datetime.now()
    cursor.execute('''
        INSERT INTO notion_cache (tabela_nome, dados_json, ultima_atualizacao)
        VALUES (?, ?, ?)
        ON CONFLICT(tabela_nome) DO UPDATE SET 
        dados_json = excluded.dados_json,
        ultima_atualizacao = excluded.ultima_atualizacao
    ''', (tabela_nome, json_str, agora))
    conn.commit()
    conn.close()

def ler_do_banco(tabela_nome):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT dados_json FROM notion_cache WHERE tabela_nome = ?", (tabela_nome,))
    resultado = cursor.fetchone()
    conn.close()
    if resultado: return json.loads(resultado[0])
    return None

# ==========================================
# 2. UTILS E INTEGRAÇÃO NOTION
# ==========================================
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
            else: break
        except Exception: break
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
            if prop["type"] == "title" and prop.get("title"): return prop["title"][0]["plain_text"]
            if prop["type"] == "number" and prop.get("number") is not None: return str(prop["number"])
            if prop["type"] == "date" and prop.get("date"): return prop["date"]["start"]
    except: pass
    return "Outros / Não Informado"

def normalizar_nome(nome):
    """Limpa acentos, espaços duplos e maiúsculas para o Cruzamento Mágico"""
    if not nome or nome == "Outros / Não Informado": return ""
    n = str(nome).strip().upper()
    return unicodedata.normalize('NFKD', n).encode('ASCII', 'ignore').decode('utf-8')

# ==========================================
# 3. ROTAS DA API
# ==========================================
def sincronizar_tudo():
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        f1 = executor.submit(buscar_itens_notion, DB_COLABORADORES)
        f2 = executor.submit(buscar_itens_notion, DB_DESLIGAMENTOS)
        f3 = executor.submit(buscar_itens_notion, DB_ATESTADOS)
        f4 = executor.submit(buscar_itens_notion, DB_ADVERTENCIAS)
        f5 = executor.submit(buscar_itens_notion, DB_FREQUENCIA)
        f6 = executor.submit(buscar_itens_notion, DB_DESEMPENHO)
        f7 = executor.submit(buscar_itens_notion, DB_ARMARIOS)

        salvar_no_banco("colaboradores", f1.result())
        salvar_no_banco("desligamentos", f2.result())
        salvar_no_banco("atestados", f3.result())
        salvar_no_banco("advertencias", f4.result())
        salvar_no_banco("frequencia", f5.result())
        salvar_no_banco("desempenho", f6.result())
        salvar_no_banco("armarios", f7.result())

@app.get("/api/sincronizar")
def endpoint_sincronizar(background_tasks: BackgroundTasks):
    background_tasks.add_task(sincronizar_tudo)
    return {"sucesso": True, "mensagem": "Sincronização iniciada."}

# ----- O NOVO MOTOR DE CARTÃO DE PONTO (SAP -> NOTION) -----
@app.post("/api/processar_ponto")
async def processar_arquivo_ponto(arquivo: UploadFile = File(...)):
    try:
        conteudo = await arquivo.read()
        
        # Lê o Excel que a pessoa arrastou na tela
        try:
            df = pd.read_excel(io.BytesIO(conteudo), header=None)
        except Exception as e:
            return {"sucesso": False, "erro": "Formato de arquivo inválido. Envie o sap_009.xls gerado pelo sistema."}

        # 1. Puxa os salários e nomes atualizados do Banco Local
        colabs = ler_do_banco("colaboradores") or []
        dict_salarios = {}
        for c in colabs:
            props = c.get("properties", {})
            nome = extrair_texto(props, "Funcionário")
            if nome == "Outros / Não Informado": nome = extrair_texto(props, "Nome")
            if nome == "Outros / Não Informado":
                for k, v in props.items():
                    if v.get("type") == "title" and v.get("title"):
                        nome = v["title"][0]["plain_text"]
                        break
            
            sal_str = extrair_texto(props, "Salário (R$)")
            salario = 0.0
            try: salario = float(sal_str)
            except: pass
            
            setor = extrair_texto(props, "Setor")
            
            # Cria a chave secreta de cruzamento (ex: VITORIA CANOSSA)
            nome_norm = normalizar_nome(nome)
            dict_salarios[nome_norm] = {"salario": salario, "setor": setor, "nome_original": nome}

        # 2. Hackeando o Excel do SAP linha por linha
        resultados = []
        nome_atual_sap = None
        
        for i, row in df.iterrows():
            row_str = ' | '.join([str(x) if pd.notna(x) else "" for x in row.values])
            
            # Acha o nome do funcionário no bloco
            if 'Funcionário' in row_str and ':' in row_str:
                parts = row_str.split('Funcionário')[1].split(':')
                if len(parts) > 1:
                    emp_info = parts[1].replace('|', '').strip()
                    emp_parts = emp_info.split(' ', 1)
                    if len(emp_parts) == 2:
                        nome_atual_sap = normalizar_nome(emp_parts[1])
            
            # Acha o Total Descontado no bloco de Resumo
            if 'Tot Descontado' in row_str and nome_atual_sap:
                time_val = None
                for cell in row.values:
                    if pd.notna(cell) and isinstance(cell, str) and ':' in cell and len(cell.strip()) <= 6:
                        time_val = cell.strip()
                        break
                
                if time_val:
                    try:
                        # Matemática do RH (Horas -> Decimais -> Reais)
                        h, m = time_val.split(":")
                        horas_decimais = int(h) + (int(m) / 60.0)
                        
                        # Cruza o nome do SAP com o banco do Notion
                        info_func = dict_salarios.get(nome_atual_sap)
                        
                        if info_func:
                            salario = info_func["salario"]
                            if salario <= 0: salario = 2270.22 # Fallback padrão caso esteja vazio
                            
                            valor_hora = salario / 220.0
                            desconto_rs = horas_decimais * valor_hora
                            
                            resultados.append({
                                "nome": info_func["nome_original"],
                                "setor": info_func["setor"],
                                "salario_base": salario,
                                "horas_desconto": time_val,
                                "valor_desconto": round(desconto_rs, 2)
                            })
                        else:
                            # Caso a pessoa não exista no Notion (Terceirizado ou Recém Contratado)
                            resultados.append({
                                "nome": emp_parts[1].strip() + " (Não achou no Notion)",
                                "setor": "-",
                                "salario_base": 0.0,
                                "horas_desconto": time_val,
                                "valor_desconto": 0.0
                            })
                    except: pass
                    nome_atual_sap = None # Zera para o próximo funcionário

        # Retorna a lista organizada!
        return {"sucesso": True, "processados": len(resultados), "dados": resultados}
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

@app.get("/api/dashboard/kpis")
def obter_kpis_do_banco(mes: int = None, ano: int = None, setor: str = "Todos"):
    hoje = datetime.now()
    mes_int = mes if mes else hoje.month
    ano_int = ano if ano else hoje.year

    inicio_mes = f"{ano_int}-{mes_int:02d}-01"
    ultimo_dia = calendar.monthrange(ano_int, mes_int)[1]
    fim_mes_str = f"{ano_int}-{mes_int:02d}-{ultimo_dia}"

    todos_colab = ler_do_banco("colaboradores") or []
    todos_deslig = ler_do_banco("desligamentos") or []
    todos_atestados = ler_do_banco("atestados") or []
    todos_adv = ler_do_banco("advertencias") or []
    todos_freq = ler_do_banco("frequencia") or []
    avaliacoes_itens = ler_do_banco("desempenho") or []
    armarios_itens = ler_do_banco("armarios") or []

    if len(todos_colab) == 0:
        sincronizar_tudo()
        todos_colab = ler_do_banco("colaboradores") or []
        todos_deslig = ler_do_banco("desligamentos") or []
        todos_atestados = ler_do_banco("atestados") or []
        todos_adv = ler_do_banco("advertencias") or []
        todos_freq = ler_do_banco("frequencia") or []
        avaliacoes_itens = ler_do_banco("desempenho") or []
        armarios_itens = ler_do_banco("armarios") or []

    ativos_itens = [i for i in todos_colab if extrair_texto(i.get("properties", {}), "Status") == "Ativo"]
    
    admissoes_itens = []
    for i in todos_colab:
        dt = extrair_texto(i.get("properties", {}), "Data de admissão")
        if dt != "Outros / Não Informado" and inicio_mes <= dt[:10] <= fim_mes_str: admissoes_itens.append(i)
            
    desligamentos_itens, desligamentos_ano = [], []
    for i in todos_deslig:
        dt = extrair_texto(i.get("properties", {}), "Data de Desligamento")
        if dt != "Outros / Não Informado":
            if inicio_mes <= dt[:10] <= fim_mes_str: desligamentos_itens.append(i)
            if dt[:4] == str(ano_int): desligamentos_ano.append(i)

    atestados_itens = [i for i in todos_atestados if extrair_texto(i.get("properties", {}), "Data de Entrega") != "Outros / Não Informado" and inicio_mes <= extrair_texto(i.get("properties", {}), "Data de Entrega")[:10] <= fim_mes_str]
    advertencias_itens = [i for i in todos_adv if extrair_texto(i.get("properties", {}), "Data da Advertência") != "Outros / Não Informado" and inicio_mes <= extrair_texto(i.get("properties", {}), "Data da Advertência")[:10] <= fim_mes_str]
    faltas_itens = [i for i in todos_freq if extrair_texto(i.get("properties", {}), "Data") != "Outros / Não Informado" and inicio_mes <= extrair_texto(i.get("properties", {}), "Data")[:10] <= fim_mes_str]

    setores_unicos = set()
    for item in ativos_itens:
        s = extrair_texto(item.get("properties", {}), "Setor")
        if s and s != "Outros / Não Informado": setores_unicos.add(s)
    lista_setores = sorted(list(setores_unicos))

    if setor != "Todos":
        ativos_itens = [i for i in ativos_itens if extrair_texto(i.get("properties", {}), "Setor") == setor]
        admissoes_itens = [i for i in admissoes_itens if extrair_texto(i.get("properties", {}), "Setor") == setor]
        desligamentos_itens = [i for i in desligamentos_itens if extrair_texto(i.get("properties", {}), "Setor") == setor]
        atestados_itens = [i for i in atestados_itens if extrair_texto(i.get("properties", {}), "Setor") == setor]
        advertencias_itens = [i for i in advertencias_itens if extrair_texto(i.get("properties", {}), "Setor") == setor]
        faltas_itens = [i for i in faltas_itens if extrair_texto(i.get("properties", {}), "Setor") == setor]
        avaliacoes_itens = [i for i in avaliacoes_itens if extrair_texto(i.get("properties", {}), "Setor") == setor]
        desligamentos_ano = [i for i in desligamentos_ano if extrair_texto(i.get("properties", {}), "Setor") == setor]
        armarios_itens = [i for i in armarios_itens if extrair_texto(i.get("properties", {}), "Setor") == setor]

    total_ativos = len(ativos_itens)
    dict_perfis = {}
    
    def get_nome_correto(props):
        nome = extrair_texto(props, "Funcionário")
        if nome == "Outros / Não Informado": nome = extrair_texto(props, "Nome")
        if nome == "Outros / Não Informado":
            for k, v in props.items():
                if v.get("type") == "title" and v.get("title"): return v["title"][0]["plain_text"]
        return nome

    def iniciar_perfil(nome):
        if nome not in dict_perfis:
            dict_perfis[nome] = {"cargo": "-", "setor": "-", "tempo_casa": "-", "salario": 0.0, "historico_atestados": [], "historico_advertencias": [], "faltas_dias": 0, "atrasos": 0, "nota_desempenho": 0.0, "qtd_aval": 0}

    alertas_aniversarios, alertas_contratos, alertas_ferias = [], [], []
    for item in ativos_itens:
        props = item.get("properties", {})
        nome = get_nome_correto(props)
        iniciar_perfil(nome)
        dict_perfis[nome]["cargo"] = extrair_texto(props, "Cargo")
        dict_perfis[nome]["setor"] = extrair_texto(props, "Setor")
        
        sal_str = extrair_texto(props, "Salário (R$)")
        if sal_str != "Outros / Não Informado":
            try: dict_perfis[nome]["salario"] = float(sal_str)
            except: pass
        
        adm_str = extrair_texto(props, "Data de admissão")
        if adm_str != "Outros / Não Informado":
            try:
                data_admissao = datetime.strptime(adm_str[:10], "%Y-%m-%d")
                diff = hoje - data_admissao
                anos, meses = diff.days // 365, (diff.days % 365) // 30
                dict_perfis[nome]["tempo_casa"] = f"{anos} ano(s) e {meses} mês(es)" if anos > 0 else f"{meses} mês(es)"
                if diff.days >= 365:
                    dias_para_dobrar = (365 * 2) - diff.days
                    if -365 < dias_para_dobrar <= 120: alertas_ferias.append({"nome": nome, "dias_restantes": dias_para_dobrar, "setor": dict_perfis[nome]["setor"]})
                venc_45, venc_90 = data_admissao + timedelta(days=45), data_admissao + timedelta(days=90)
                if venc_45.year == ano_int and venc_45.month == mes_int: alertas_contratos.append({"nome": nome, "dia": venc_45.day, "tipo": "45 Dias"})
                if venc_90.year == ano_int and venc_90.month == mes_int: alertas_contratos.append({"nome": nome, "dia": venc_90.day, "tipo": "90 Dias"})
            except: pass
            
        nasc_str = extrair_texto(props, "Data de Nascimento")
        if nasc_str == "Outros / Não Informado": nasc_str = extrair_texto(props, "Nascimento")
        if nasc_str != "Outros / Não Informado":
            try:
                if int(nasc_str.split("-")[1]) == mes_int: alertas_aniversarios.append({"nome": nome, "dia": int(nasc_str.split("-")[2])})
            except: pass

    alertas_aniversarios = sorted(alertas_aniversarios, key=lambda x: x["dia"])
    alertas_contratos = sorted(alertas_contratos, key=lambda x: x["dia"])
    alertas_ferias = sorted(alertas_ferias, key=lambda x: x["dias_restantes"])

    total_faltas_inteiras, total_atrasos, total_perdas_r, total_horas_extras = 0, 0, 0.0, 0.0
    dict_ranking, dict_he_setor = {}, {}

    for item in faltas_itens:
        props = item.get("properties", {})
        nome = get_nome_correto(props)
        setor_freq = extrair_texto(props, "Setor")
        iniciar_perfil(nome)
        
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

        prop_he = props.get("Horas Extras") or props.get("HE") or props.get("Valor HE") or {}
        qtd_he = prop_he.get("number") if prop_he.get("type") == "number" else 0
        if qtd_he and qtd_he > 0:
            total_horas_extras += qtd_he
            if setor_freq not in dict_he_setor: dict_he_setor[setor_freq] = 0
            dict_he_setor[setor_freq] += qtd_he

    ranking_faltas = sorted([{"nome": k, "faltas": v} for k, v in dict_ranking.items()], key=lambda x: x["faltas"], reverse=True)[:5]
    grafico_he = sorted([{"setor": k, "horas": v} for k, v in dict_he_setor.items()], key=lambda x: x["horas"], reverse=True)

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
        data_str = extrair_texto(props, "Data de Entrega")
        if cid and cid != "Outros / Não Informado":
            label_cid = f"{cid} - {motivo}" if motivo != "Outros / Não Informado" else cid
            dict_cids[label_cid] = dict_cids.get(label_cid, 0) + 1
            dict_perfis[nome]["historico_atestados"].append({"data": data_str[:10] if data_str != "Outros / Não Informado" else "-", "motivo": label_cid})
        else:
            dict_perfis[nome]["historico_atestados"].append({"data": data_str[:10] if data_str != "Outros / Não Informado" else "-", "motivo": motivo})
    
    ranking_atestados = sorted([{"nome": k, "atestados": v} for k, v in dict_ranking_atestados.items()], key=lambda x: x["atestados"], reverse=True)[:5]
    ranking_medicos = sorted([{"nome": k, "quantidade": v} for k, v in dict_medicos.items()], key=lambda x: x["quantidade"], reverse=True)[:7]
    ranking_cids = sorted([{"nome": k, "quantidade": v} for k, v in dict_cids.items()], key=lambda x: x["quantidade"], reverse=True)[:10]

    dict_adv = {}
    for item in advertencias_itens:
        props = item.get("properties", {})
        nome = get_nome_correto(props)
        iniciar_perfil(nome)
        motivo = extrair_texto(props, "Motivo")
        if motivo == "Outros / Não Informado": motivo = extrair_texto(props, "Tipo")
        dict_adv[motivo] = dict_adv.get(motivo, 0) + 1
        data_str = extrair_texto(props, "Data da Advertência")
        dict_perfis[nome]["historico_advertencias"].append({"data": data_str[:10] if data_str != "Outros / Não Informado" else "-", "motivo": motivo})
        
    grafico_advertencias = [{"name": k, "value": v} for k, v in dict_adv.items()]

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
            
    grafico_radar = [{"subject": c, "A": (radar_somas[c] / radar_cont[c]) if radar_cont[c] > 0 else 4.0, "fullMark": 5} for c in competencias]

    dict_setores = {}
    for item in atestados_itens:
        s = extrair_texto(item.get("properties", {}), "Setor")
        if s not in dict_setores: dict_setores[s] = {"setor": s, "atestados": 0, "faltas": 0}
        dict_setores[s]["atestados"] += 1
    for item in faltas_itens:
        s = extrair_texto(item.get("properties", {}), "Setor")
        if s not in dict_setores: dict_setores[s] = {"setor": s, "atestados": 0, "faltas": 0}
        dict_setores[s]["faltas"] += 1
    grafico_setores = list(dict_setores.values())

    meses_nomes = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    contagem_meses, dict_motivos = {m: 0 for m in meses_nomes}, {}
    for item in desligamentos_ano:
        props = item.get("properties", {})
        dt = extrair_texto(props, "Data de Desligamento")
        if dt != "Outros / Não Informado":
            mes_idx = int(dt.split("-")[1]) - 1
            contagem_meses[meses_nomes[mes_idx]] += 1
        motivo = extrair_texto(props, "Motivo de Desligamento")
        if motivo not in dict_motivos: dict_motivos[motivo] = 0
        dict_motivos[motivo] += 1
        
    grafico_turnover = [{"mes": mes, "turnover": round((contagem_meses[mes] / total_ativos) * 100, 1) if total_ativos > 0 else 0} for mes in meses_nomes]
    grafico_motivos = [{"name": k, "value": v} for k, v in dict_motivos.items()]

    dict_headcount = {}
    for item in ativos_itens:
        s = extrair_texto(item.get("properties", {}), "Setor")
        if s not in dict_headcount: dict_headcount[s] = 0
        dict_headcount[s] += 1
    grafico_headcount = sorted([{"setor": k, "quantidade": v} for k, v in dict_headcount.items()], key=lambda x: x["quantidade"], reverse=True)
    turnover_atual = f"{(len(desligamentos_itens) / total_ativos) * 100:.1f}%" if total_ativos > 0 else "0.0%"

    lista_armarios = []
    for item in armarios_itens:
        props = item.get("properties", {})
        num_str = extrair_texto(props, "armario_numero")
        if num_str == "Outros / Não Informado":
             for k, v in props.items():
                if v.get("type") == "title" and v.get("title"):
                    num_str = v["title"][0]["plain_text"]
                    break
        num_val = 0
        try:
             clean_num = ''.join(filter(str.isdigit, num_str))
             num_val = int(clean_num) if clean_num else 0
        except: pass

        dono = extrair_texto(props, "nome_funcionario")
        if dono == "Outros / Não Informado":
            for k, v in props.items():
                if v.get("type") == "title" and v.get("title"):
                    dono = v["title"][0]["plain_text"]
                    break
        if dono == "Outros / Não Informado": dono = None

        status = extrair_texto(props, "status")
        status_clean = "Livre"
        if not status or status == "Outros / Não Informado":
             if dono: status_clean = "Ocupado"
             else: status_clean = "Livre"
        else:
            status_lower = status.lower()
            if "ocupado" in status_lower: status_clean = "Ocupado"
            elif "manuten" in status_lower or "indispon" in status_lower: status_clean = "Manutenção"
            elif "livre" in status_lower or "dispon" in status_lower: status_clean = "Livre"
            
        lista_armarios.append({"num": num_str if num_str != "Outros / Não Informado" else "?", "sort_val": num_val, "dono": dono, "status": status_clean})

    lista_armarios = sorted(lista_armarios, key=lambda x: x["sort_val"])

    return {
        "funcionarios": total_ativos, "admissoes": len(admissoes_itens), "desligamentos": len(desligamentos_itens), "turnover": turnover_atual,     
        "atestados": len(atestados_itens), "advertencias": len(advertencias_itens), "faltas": total_faltas_inteiras, "atrasos": total_atrasos,
        "custo_absenteismo": total_perdas_r, "avaliacoes": len(avaliacoes_itens),
        "graficoSetores": grafico_setores, "graficoTurnover": grafico_turnover, "graficoMotivos": grafico_motivos, "graficoHeadcount": grafico_headcount,
        "alertasAniversarios": alertas_aniversarios, "alertasContratos": alertas_contratos,
        "graficoAdvertencias": grafico_advertencias, "rankingFaltas": ranking_faltas, 
        "rankingAtestados": ranking_atestados, "rankingMedicos": ranking_medicos, "rankingCids": ranking_cids,       
        "graficoRadar": grafico_radar, "perfis360": dict_perfis,
        "alertasFerias": alertas_ferias, "totalHorasExtras": total_horas_extras, "graficoHorasExtras": grafico_he,
        "armarios": lista_armarios, "setoresDisponiveis": lista_setores
    }
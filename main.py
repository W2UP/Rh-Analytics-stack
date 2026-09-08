from fastapi import FastAPI, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
import re
import openpyxl
import warnings

warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')
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

CACHE_RELACOES = {}

def carregar_cache_relacoes():
    global CACHE_RELACOES
    if not CACHE_RELACOES:
        colabs = ler_do_banco("colaboradores") or []
        for c in colabs:
            page_id = c.get("id")
            props = c.get("properties", {})
            for k, v in props.items():
                if v.get("type") == "title" and v.get("title"):
                    nome = v.get("title")[0]["plain_text"]
                    if page_id: CACHE_RELACOES[page_id] = nome
                    break
    return CACHE_RELACOES

def formatar_setor(setor_nome):
    if not setor_nome or setor_nome == "Outros / Não Informado" or setor_nome == "-": return "Outros"
    s = str(setor_nome).strip().title()
    replaces = {"Rh": "RH", "Dho": "DHO", "Ti": "TI", "Pcp": "PCP", "Uchoa": "Uchoa"}
    return replaces.get(s, s)

def iniciar_banco_dados():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS notion_cache (tabela_nome TEXT PRIMARY KEY, dados_json TEXT, ultima_atualizacao TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS historico_folha (id INTEGER PRIMARY KEY AUTOINCREMENT, mes INTEGER, ano INTEGER, nome_funcionario TEXT, setor TEXT, salario_base REAL, horas_desconto TEXT, valor_desconto REAL, data_lancamento TIMESTAMP, faltas_dias REAL DEFAULT 0.0)''')
    try: cursor.execute("ALTER TABLE historico_folha ADD COLUMN faltas_dias REAL DEFAULT 0.0")
    except: pass
    conn.commit()
    conn.close()

iniciar_banco_dados()

def salvar_no_banco(tabela_nome, dados_lista):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    json_str = json.dumps(dados_lista)
    agora = datetime.now()
    cursor.execute('''INSERT INTO notion_cache (tabela_nome, dados_json, ultima_atualizacao) VALUES (?, ?, ?) ON CONFLICT(tabela_nome) DO UPDATE SET dados_json = excluded.dados_json, ultima_atualizacao = excluded.ultima_atualizacao''', (tabela_nome, json_str, agora))
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

class LoginData(BaseModel):
    usuario: str
    senha: str

USUARIOS_PERMITIDOS = {"diretoria": "@senha123", "gerencia": "@senha456", "rh": "@rh2026"}

@app.post("/api/login")
def validar_login(dados: LoginData):
    usuario_digitado = dados.usuario.lower()
    if usuario_digitado in USUARIOS_PERMITIDOS and USUARIOS_PERMITIDOS[usuario_digitado] == dados.senha: return {"sucesso": True, "usuario": usuario_digitado}
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

def extrair_valor_prop(prop):
    try:
        if prop["type"] == "select" and prop.get("select"): return prop["select"]["name"]
        if prop["type"] == "status" and prop.get("status"): return prop["status"]["name"]
        if prop["type"] == "rich_text" and prop.get("rich_text"): return prop["rich_text"][0]["plain_text"]
        if prop["type"] == "rollup" and prop.get("rollup"):
            arr = prop["rollup"].get("array", [])
            if arr:
                if arr[0].get("title"): return arr[0]["title"][0]["plain_text"]
                if arr[0].get("rich_text"): return arr[0]["rich_text"][0]["plain_text"]
                if arr[0].get("select"): return arr[0]["select"]["name"]
        if prop["type"] == "title" and prop.get("title"): return prop["title"][0]["plain_text"]
        if prop["type"] == "number" and prop.get("number") is not None: return str(prop["number"])
        if prop["type"] == "date" and prop.get("date"): return prop["date"]["start"]
        if prop["type"] == "relation" and prop.get("relation"):
            rel_id = prop["relation"][0]["id"]
            cache = carregar_cache_relacoes()
            if rel_id in cache: return cache[rel_id]
    except: pass
    return "Outros / Não Informado"

def extrair_texto(propriedades, nome_coluna):
    if nome_coluna in propriedades: return extrair_valor_prop(propriedades[nome_coluna])
    for k, v in propriedades.items():
        if nome_coluna.lower() in k.lower(): return extrair_valor_prop(v)
    return "Outros / Não Informado"

def get_nome_correto(props, is_atestado=False):
    nome = extrair_texto(props, "funcion")
    if nome == "Outros / Não Informado": nome = extrair_texto(props, "nome")
    if nome == "Outros / Não Informado": nome = extrair_texto(props, "colab")
    if nome == "Outros / Não Informado" or not str(nome).strip():
        for k, v in props.items():
            if v.get("type") == "title" and v.get("title"):
                nome_bruto = v["title"][0]["plain_text"]
                nome = re.split(r'[-–—]', nome_bruto)[0].strip()
                break
    return nome if nome else "Outros / Não Informado"

def normalizar_nome(nome):
    if not nome or nome == "Outros / Não Informado": return ""
    n = str(nome).strip().upper()
    n = unicodedata.normalize('NFKD', n).encode('ASCII', 'ignore').decode('utf-8')
    palavras = n.split()
    palavras_limpas = [p for p in palavras if p not in ["DE", "DA", "DO", "DAS", "DOS", "E"]]
    return " ".join(palavras_limpas)

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
    global CACHE_RELACOES
    CACHE_RELACOES.clear() 
    background_tasks.add_task(sincronizar_tudo)
    return {"sucesso": True, "mensagem": "Sincronização iniciada."}

@app.post("/api/processar_ponto")
async def processar_arquivo_ponto(arquivo: UploadFile = File(...)):
    try:
        conteudo = await arquivo.read()
        try: df = pd.read_excel(io.BytesIO(conteudo), header=None, engine='xlrd')
        except Exception as e: return {"sucesso": False, "erro": f"Erro Técnico do Python: {str(e)}"}
        colabs = ler_do_banco("colaboradores") or []
        dict_salarios = {}
        for c in colabs:
            props = c.get("properties", {})
            nome = get_nome_correto(props)
            sal_str = extrair_texto(props, "Salário (R$)")
            salario = 0.0
            try: salario = float(sal_str)
            except: pass
            setor = extrair_texto(props, "Setor")
            nome_norm = normalizar_nome(nome)
            dict_salarios[nome_norm] = {"salario": salario, "setor": setor, "nome_original": nome}

        resultados = []
        nome_atual_sap = None
        setor_atual_sap = None
        faltas_dias_atual = 0.0
        
        nomes_ignorados = [
            "Ana Carolina Sant Ana Vieira", "Debora Perpetua Barbosa", "Elias Honório Garcia",
            "Gabriel Felipe Aparecido De Moraes Braz", "Gleice Kely Da Silva Rodrigues Barroso",
            "Priscila Aparecida Cerqueira", "Vitoria Carolina Novaes Luiz"
        ]
        
        for i, row in df.iterrows():
            row_str = ' | '.join([str(x) if pd.notna(x) else "" for x in row.values])
            if 'Funcionário' in row_str and ':' in row_str:
                parts = row_str.split('Funcionário')[1].split(':')
                if len(parts) > 1:
                    emp_info = parts[1].replace('|', '').strip()
                    emp_parts = emp_info.split(' ', 1)
                    if len(emp_parts) == 2:
                        nome_temp = normalizar_nome(emp_parts[1])
                        pular_funcionario = False
                        for n_block in nomes_ignorados:
                            if normalizar_nome(n_block) in nome_temp:
                                pular_funcionario = True
                                break
                        if pular_funcionario: nome_atual_sap = None
                        else: nome_atual_sap = nome_temp
                        setor_atual_sap = None 
                        faltas_dias_atual = 0.0
                        
            if 'Setor' in row_str and ':' in row_str:
                parts = row_str.split(':')
                if len(parts) > 1:
                    sector_name_parts = parts[1].split('|')
                    found = [s.strip() for s in sector_name_parts if s.strip() and not s.strip().isdigit()]
                    if found: setor_atual_sap = formatar_setor(found[0])
            if setor_atual_sap and ("UCHOA" in setor_atual_sap.upper() or "UCHÔA" in setor_atual_sap.upper()):
                if 'Tot Descontado' in row_str: nome_atual_sap = None 
                continue 

            if nome_atual_sap and 'FALTA' in row_str:
                vals = []
                for j in [4, 5, 6, 7]: 
                    if j < len(row.values) and pd.notna(row.values[j]) and str(row.values[j]).strip() != "":
                        vals.append(str(row.values[j]).strip().upper())
                fc = sum(1 for v in vals if 'FALTA' in v)
                if fc >= 3: faltas_dias_atual += 1.0   
                elif fc == 2: faltas_dias_atual += 0.5   
            
            if 'Tot Descontado' in row_str and nome_atual_sap:
                time_val = None
                for cell in row.values:
                    if pd.notna(cell) and isinstance(cell, str) and ':' in cell and len(cell.strip()) <= 6:
                        time_val = cell.strip()
                        break
                if time_val:
                    try:
                        info_func = dict_salarios.get(nome_atual_sap)
                        if info_func:
                            h, m = time_val.split(":")
                            horas_decimais = int(h) + (int(m) / 60.0)
                            salario = info_func["salario"]
                            if salario <= 0: salario = 2270.22 
                            valor_hora = salario / 220.0
                            desconto_rs = horas_decimais * valor_hora
                            resultados.append({
                                "nome": info_func["nome_original"],
                                "setor": formatar_setor(info_func.get("setor")),
                                "salario_base": salario,
                                "horas_desconto": time_val,
                                "valor_desconto": round(desconto_rs, 2),
                                "faltas_dias": faltas_dias_atual
                            })
                        else:
                            nome_bonito = emp_parts[1].strip().title()
                            resultados.append({
                                "nome": f"{nome_bonito} (Não achou)",
                                "setor": setor_atual_sap if setor_atual_sap else "Outros",
                                "salario_base": 0.0,
                                "horas_desconto": time_val,
                                "valor_desconto": 0.0,
                                "faltas_dias": faltas_dias_atual
                            })
                    except: pass
                    nome_atual_sap = None 

        return {"sucesso": True, "processados": len(resultados), "dados": resultados}
    except Exception as e: return {"sucesso": False, "erro": str(e)}

def somar_horas(h1, h2):
    if not h1: return h2
    if not h2: return h1
    try:
        def para_minutos(h_str):
            partes = h_str.split(':')
            return int(partes[0]) * 60 + int(partes[1])
        
        total_min = para_minutos(h1) + para_minutos(h2)
        horas = total_min // 60
        minutos = total_min % 60
        return f"{horas:02d}:{minutos:02d}"
    except:
        return h1

@app.post("/api/rpa_horas_extras")
async def rpa_horas_extras(arquivo_sap: UploadFile = File(...), arquivo_escritorio: UploadFile = File(...)):
    try:
        conteudo_sap = await arquivo_sap.read()
        df_sap = pd.read_excel(io.BytesIO(conteudo_sap), header=None, engine='xlrd')

        dados_sap = {}
        current_norm = None
        faltas_dias_atual = 0.0
        dsr_perdidos_atual = 0
        teve_falta_integral_na_semana = False

        for i, row in df_sap.iterrows():
            row_str = ' | '.join([str(x).strip() if pd.notna(x) else "" for x in row.values])
            
            if 'Funcionário' in row_str and ':' in row_str:
                if current_norm and current_norm in dados_sap:
                    if teve_falta_integral_na_semana: 
                        dsr_perdidos_atual += 1
                    
                    dados_sap[current_norm]["faltas_dias"] = faltas_dias_atual
                    dados_sap[current_norm]["dsr_perdidos"] = dsr_perdidos_atual
                
                parts = row_str.split(':')
                if len(parts) > 1:
                    emp_info = parts[1].replace('|', '').strip()
                    emp_parts = emp_info.split(' ', 1)
                    if len(emp_parts) == 2:
                        current_norm = normalizar_nome(emp_parts[1])
                        dados_sap[current_norm] = {"he_50": None, "he_100": None, "adc_noturno": None, "faltas_dias": 0.0, "dsr_perdidos": 0}
                        faltas_dias_atual = 0.0
                        dsr_perdidos_atual = 0
                        teve_falta_integral_na_semana = False
                    else:
                        current_norm = None
                        
            if current_norm:
                if 'FALTA' in row_str:
                    vals = []
                    for j in [4, 5, 6, 7]: 
                        if j < len(row.values) and pd.notna(row.values[j]) and str(row.values[j]).strip() != "":
                            vals.append(str(row.values[j]).strip().upper())
                    fc = sum(1 for v in vals if 'FALTA' in v)
                    if fc >= 3: 
                        faltas_dias_atual += 1.0
                        teve_falta_integral_na_semana = True

                if 'DOM' in row_str.upper():
                    if teve_falta_integral_na_semana:
                        dsr_perdidos_atual += 1
                    teve_falta_integral_na_semana = False

                if 'Extra A 050%' in row_str:
                    match = re.search(r'Extra A 050%\s*:\s*(\d{1,3}:\d{2})', row_str)
                    if match: dados_sap[current_norm]["he_50"] = somar_horas(dados_sap[current_norm]["he_50"], match.group(1))

                if 'Ext Adi A 050%' in row_str:
                    match = re.search(r'Ext Adi A 050%\s*:\s*(\d{1,3}:\d{2})', row_str)
                    if match: dados_sap[current_norm]["he_50"] = somar_horas(dados_sap[current_norm]["he_50"], match.group(1))
                    
                if 'Extra A 100%' in row_str:
                    match = re.search(r'Extra A 100%\s*:\s*(\d{1,3}:\d{2})', row_str)
                    if match: dados_sap[current_norm]["he_100"] = somar_horas(dados_sap[current_norm]["he_100"], match.group(1))

                if 'Ext Adi A 100%' in row_str:
                    match = re.search(r'Ext Adi A 100%\s*:\s*(\d{1,3}:\d{2})', row_str)
                    if match: dados_sap[current_norm]["he_100"] = somar_horas(dados_sap[current_norm]["he_100"], match.group(1))

                if 'Adc Noturno' in row_str:
                    match = re.search(r'(\d{1,3}:\d{2})', row_str.replace('Adc Noturno', ''))
                    if match: dados_sap[current_norm]["adc_noturno"] = match.group(1)

        if current_norm and current_norm in dados_sap:
            if teve_falta_integral_na_semana: dsr_perdidos_atual += 1
            dados_sap[current_norm]["faltas_dias"] = faltas_dias_atual
            dados_sap[current_norm]["dsr_perdidos"] = dsr_perdidos_atual

        dados_ativos = {}
        for nome, info in dados_sap.items():
            if info["he_50"] or info["he_100"] or info["adc_noturno"] or info["faltas_dias"] > 0:
                info["encontrado"] = False
                dados_ativos[nome] = info

        conteudo_escritorio = await arquivo_escritorio.read()
        wb = openpyxl.load_workbook(io.BytesIO(conteudo_escritorio))
        processados = 0

        for ws in wb.worksheets:
            col_nome = col_he50 = col_he100 = col_noturno = col_faltas_dsr = header_row = None
            for r in range(1, 15):
                for c in range(1, ws.max_column + 1):
                    val = str(ws.cell(row=r, column=c).value or "").strip().lower()
                    if 'nome' in val and 'colaborador' in val: col_nome = c
                    elif 'adc 50%' in val: col_he50 = c
                    elif 'adc 100%' in val: col_he100 = c
                    elif 'noturno' in val: col_noturno = c
                    elif 'faltas' in val and 'dsr' in val: col_faltas_dsr = c
                if col_nome and col_he50:
                    header_row = r
                    break

            if col_nome and col_he50 and header_row:
                for r in range(header_row + 1, ws.max_row + 1):
                    nome_cell = ws.cell(row=r, column=col_nome).value
                    if nome_cell:
                        norm_excel = normalizar_nome(str(nome_cell))
                        nome_encontrado_dict = None
                        if norm_excel in dados_ativos:
                            nome_encontrado_dict = norm_excel
                        else:
                            for nome_ativo in dados_ativos.keys():
                                if nome_ativo in norm_excel or norm_excel in nome_ativo:
                                    nome_encontrado_dict = nome_ativo
                                    break
                                    
                        if nome_encontrado_dict:
                            info = dados_ativos[nome_encontrado_dict]
                            if info["he_50"] and col_he50: ws.cell(row=r, column=col_he50).value = info["he_50"]
                            if info["he_100"] and col_he100: ws.cell(row=r, column=col_he100).value = info["he_100"]
                            if info.get("adc_noturno") and col_noturno: ws.cell(row=r, column=col_noturno).value = info["adc_noturno"]
                                
                            if info.get("faltas_dias", 0) > 0 and col_faltas_dsr:
                                qtd_f = info["faltas_dias"]
                                qtd_dsr = info.get("dsr_perdidos", 0)
                                f_str = str(int(qtd_f)) if qtd_f.is_integer() else str(qtd_f)
                                d_str = str(int(qtd_dsr))
                                ws.cell(row=r, column=col_faltas_dsr).value = f"{f_str}+{d_str}dsr"
                            
                            if not info["encontrado"]:
                                info["encontrado"] = True
                                processados += 1

        nao_encontrados = [nome for nome, info in dados_ativos.items() if not info["encontrado"]]
        erros_str = "|".join(nao_encontrados) if nao_encontrados else "Nenhum"

        saida_memoria = io.BytesIO()
        wb.save(saida_memoria)
        saida_memoria.seek(0)

        return StreamingResponse(
            saida_memoria,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=ESCRITORIO_PRONTO.xlsx", 
                "Access-Control-Expose-Headers": "Content-Disposition, X-Processados, X-Nao-Encontrados",
                "X-Processados": str(processados),
                "X-Nao-Encontrados": unicodedata.normalize('NFKD', erros_str).encode('ASCII', 'ignore').decode('utf-8')
            }
        )
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

# ==========================================
# NOVO: ROBÔ RPA - CÁLCULO DE BÔNUS (SAP -> PLANILHA DE BÔNUS)
# ==========================================
@app.post("/api/rpa_bonus")
async def rpa_bonus(arquivo_sap: UploadFile = File(...), arquivo_planilha: UploadFile = File(...)):
    try:
        from collections import Counter
        conteudo_sap = await arquivo_sap.read()
        df_sap = pd.read_excel(io.BytesIO(conteudo_sap), header=None, engine='xlrd')

        dados_bonus = {}
        current_norm = None

        # 1. VARRER O SAP PARA COLETAR AS FALTAS E ATESTADOS DE ACORDO COM A REGRA DE BÔNUS
        for i, row in df_sap.iterrows():
            row_str = ' | '.join([str(x).strip() if pd.notna(x) else "" for x in row.values])
            
            if 'Funcionário' in row_str and ':' in row_str:
                parts = row_str.split(':')
                if len(parts) > 1:
                    emp_parts = parts[1].replace('|', '').strip().split(' ', 1)
                    if len(emp_parts) == 2:
                        current_norm = normalizar_nome(emp_parts[1])
                        if current_norm not in dados_bonus:
                            dados_bonus[current_norm] = {"desconto": 0.0, "motivos": []}
                    else:
                        current_norm = None
                        
            if current_norm:
                vals = []
                for j in [4, 5, 6, 7]: # Colunas de entrada e saída
                    if j < len(row.values) and pd.notna(row.values[j]) and str(row.values[j]).strip() != "":
                        vals.append(str(row.values[j]).strip().upper())
                
                # Contabiliza quantas marcações daquele tipo houveram no dia
                fc = sum(1 for v in vals if 'FALTA' in v)
                mc = sum(1 for v in vals if 'MEDIC' in v or 'ATEST' in v)
                
                # Regras de Negócio (Descontos)
                if fc >= 3:
                    dados_bonus[current_norm]["desconto"] += 1.0 # 100% de desconto
                    dados_bonus[current_norm]["motivos"].append("Falta Integral (100%)")
                elif 0 < fc <= 2:
                    dados_bonus[current_norm]["desconto"] += 0.25 # 25% de desconto
                    dados_bonus[current_norm]["motivos"].append("Meio Período Falta (25%)")
                    
                if mc >= 3:
                    dados_bonus[current_norm]["desconto"] += 0.50 # 50% de desconto
                    dados_bonus[current_norm]["motivos"].append("Atestado (50%)")
                elif 0 < mc <= 2:
                    dados_bonus[current_norm]["desconto"] += 0.25 # 25% de desconto
                    dados_bonus[current_norm]["motivos"].append("Meio Período Atestado (25%)")

        # 2. INJETAR OS DESCONTOS NA PLANILHA DE BÔNUS
        conteudo_bonus = await arquivo_planilha.read()
        wb = openpyxl.load_workbook(io.BytesIO(conteudo_bonus))
        processados = 0

        for ws in wb.worksheets:
            col_nome = col_desconto = col_motivo = header_row = None
            
            # Buscar onde começam os cabeçalhos na planilha
            for r in range(1, 25):
                for c in range(1, ws.max_column + 1):
                    val = str(ws.cell(row=r, column=c).value or "").strip().lower()
                    if 'nome' in val and 'colaborador' in val: col_nome = c
                    elif 'desconto' in val and '%' in val: col_desconto = c
                    elif 'motivo' in val: col_motivo = c
                
                if col_nome and col_desconto:
                    header_row = r
                    break

            if col_nome and col_desconto and header_row:
                for r in range(header_row + 1, ws.max_row + 1):
                    nome_cell = ws.cell(row=r, column=col_nome).value
                    if nome_cell:
                        norm_excel = normalizar_nome(str(nome_cell))
                        
                        nome_encontrado_dict = None
                        if norm_excel in dados_bonus:
                            nome_encontrado_dict = norm_excel
                        else:
                            for nome_ativo in dados_bonus.keys():
                                if nome_ativo in norm_excel or norm_excel in nome_ativo:
                                    nome_encontrado_dict = nome_ativo
                                    break
                        
                        if nome_encontrado_dict:
                            info = dados_bonus[nome_encontrado_dict]
                            
                            if info["desconto"] > 0:
                                # Trava o desconto em 100% (Evita bônus negativo)
                                desc_final = min(1.0, info["desconto"])
                                
                                # Agrupa motivos iguais. Ex: "2x Atestado (50%) + Falta Integral (100%)"
                                contagem = Counter(info["motivos"])
                                motivos_str = " + ".join([f"{qtd}x {m}" if qtd > 1 else m for m, qtd in contagem.items()])
                                
                                # Injeta na planilha
                                ws.cell(row=r, column=col_desconto).value = desc_final
                                if col_motivo:
                                    ws.cell(row=r, column=col_motivo).value = motivos_str
                                
                                processados += 1
                                # Remove do dicionário para rastrear depois quem faltou ser inserido
                                del dados_bonus[nome_encontrado_dict]

        # Descobre quem teve desconto de bônus mas não está na planilha
        nao_encontrados = [nome for nome, info in dados_bonus.items() if info["desconto"] > 0]
        erros_str = "|".join(nao_encontrados) if nao_encontrados else "Nenhum"

        saida_memoria = io.BytesIO()
        wb.save(saida_memoria)
        saida_memoria.seek(0)

        return StreamingResponse(
            saida_memoria,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=BONUS_PROCESSADO.xlsx", 
                "Access-Control-Expose-Headers": "Content-Disposition, X-Processados, X-Nao-Encontrados",
                "X-Processados": str(processados),
                "X-Nao-Encontrados": unicodedata.normalize('NFKD', erros_str).encode('ASCII', 'ignore').decode('utf-8')
            }
        )

    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

@app.post("/api/dashboard_tempo_real")
async def dashboard_tempo_real(arquivo_sap: UploadFile = File(...)):
    try:
        conteudo_sap = await arquivo_sap.read()
        df_sap = pd.read_excel(io.BytesIO(conteudo_sap), header=None, engine='xlrd')

        horas_por_funcionario = {}
        current_norm = None

        for i, row in df_sap.iterrows():
            row_str = ' | '.join([str(x).strip() if pd.notna(x) else "" for x in row.values])

            if 'Funcionário' in row_str and ':' in row_str:
                parts = row_str.split(':')
                if len(parts) > 1:
                    emp_parts = parts[1].replace('|', '').strip().split(' ', 1)
                    if len(emp_parts) == 2:
                        current_norm = normalizar_nome(emp_parts[1])
                        if current_norm not in horas_por_funcionario:
                            horas_por_funcionario[current_norm] = 0
                    else:
                        current_norm = None

            if current_norm:
                for padrao in ['Extra A 050%', 'Ext Adi A 050%', 'Extra A 100%', 'Ext Adi A 100%']:
                    if padrao in row_str:
                        match = re.search(rf'{padrao}\s*:\s*(\d{{1,3}}):(\d{{2}})', row_str)
                        if match:
                            minutos = (int(match.group(1)) * 60) + int(match.group(2))
                            horas_por_funcionario[current_norm] += minutos

        colabs = ler_do_banco("colaboradores") or []
        mapa_setores = {}
        for c in colabs:
            props = c.get("properties", {})
            nome = get_nome_correto(props)
            setor = formatar_setor(extrair_texto(props, "Setor"))
            if nome and nome != "Outros / Não Informado":
                mapa_setores[normalizar_nome(nome)] = setor

        totais_por_setor = {}
        total_geral_minutos = 0

        for nome, min_total in horas_por_funcionario.items():
            if min_total > 0:
                total_geral_minutos += min_total
                setor = mapa_setores.get(nome, "Outros / Sem Setor")
                totais_por_setor[setor] = totais_por_setor.get(setor, 0) + min_total

        h_totais = total_geral_minutos // 60
        m_totais = total_geral_minutos % 60

        grafico_setores = []
        for setor, minutos in totais_por_setor.items():
            h = minutos // 60
            m = minutos % 60
            grafico_setores.append({
                "setor": setor,
                "horas_formatadas": f"{h:02d}:{m:02d}",
                "minutos_absolutos": minutos
            })

        grafico_setores.sort(key=lambda x: x["minutos_absolutos"], reverse=True)

        return {
            "sucesso": True,
            "total_horas_empresa": f"{h_totais}:{m_totais:02d}",
            "grafico_setores": grafico_setores
        }

    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

class DadosFolha(BaseModel):
    mes: int
    ano: int
    lancamentos: list

@app.post("/api/salvar_folha")
def salvar_dados_folha(dados: DadosFolha):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        agora = datetime.now()
        cursor.execute("DELETE FROM historico_folha WHERE mes = ? AND ano = ?", (dados.mes, dados.ano))
        for lanc in dados.lancamentos:
            cursor.execute('''INSERT INTO historico_folha (mes, ano, nome_funcionario, setor, salario_base, horas_desconto, valor_desconto, data_lancamento, faltas_dias) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', (dados.mes, dados.ano, lanc['nome'], lanc['setor'], lanc['salario_base'], lanc['horas_desconto'], lanc['valor_desconto'], agora, lanc.get('faltas_dias', 0.0)))
        conn.commit()
        conn.close()
        return {"sucesso": True, "mensagem": f"{len(dados.lancamentos)} lançamentos salvos com sucesso no Banco de Dados!"}
    except Exception as e: return {"sucesso": False, "erro": str(e)}

@app.post("/api/extrair_vales")
async def extrair_vales(arquivo_pdf: UploadFile = File(...)):
    try:
        import pdfplumber
        import io
        
        conteudo_pdf = await arquivo_pdf.read()
        texto_pdf = ""
        
        with pdfplumber.open(io.BytesIO(conteudo_pdf)) as pdf:
            for page in pdf.pages:
                extract = page.extract_text()
                if extract: texto_pdf += extract + "\n"

        if not texto_pdf.strip():
            return {"sucesso": False, "erro": "O PDF é uma IMAGEM ESCANEADA sem texto selecionável. Ative a opção 'PDF Pesquisável / OCR' no seu scanner."}

        match_cliente = re.search(r'CLIENTE:\s*([^\n(]+)', texto_pdf, re.IGNORECASE)
        match_valor = re.search(r'(?:R\$|\$)\s*(\d{1,3}(?:\.\d{3})*,\d{2})', texto_pdf)
        match_parcelas = re.search(r'(?<!\d)(\d+)\s*[xX](?!\w)', texto_pdf)

        if not match_cliente or not match_valor:
            return {"sucesso": False, "erro": "Faltam informações de CLIENTE ou VALOR no documento."}

        nome_cliente = normalizar_nome(match_cliente.group(1).strip())
        valor_bruto_str = match_valor.group(1).strip()
        valor_float = float(valor_bruto_str.replace('.', '').replace(',', '.'))
        
        qtd_parcelas = int(match_parcelas.group(1)) if match_parcelas else 1
        if qtd_parcelas > 1:
            valor_float = valor_float / qtd_parcelas

        valor_final_str = f"{valor_float:.2f}".replace('.', ',')

        return {
            "sucesso": True,
            "cliente_lido": nome_cliente,
            "valor_calculado": valor_final_str,
            "parcelas": qtd_parcelas,
            "valor_original": valor_bruto_str
        }

    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

@app.post("/api/injetar_vales")
async def injetar_vales(
    arquivo_escritorio: UploadFile = File(...),
    cliente_nome: str = Form(...),
    valor_desconto: str = Form(...)
):
    try:
        conteudo_escritorio = await arquivo_escritorio.read()
        wb = openpyxl.load_workbook(io.BytesIO(conteudo_escritorio))

        inserido_com_sucesso = False
        funcionario_encontrado = ""

        for ws in wb.worksheets:
            col_nome = col_vales = header_row = None
            for r in range(1, 15):
                for c in range(1, ws.max_column + 1):
                    val = str(ws.cell(row=r, column=c).value or "").strip().lower()
                    if 'nome' in val and 'colaborador' in val: col_nome = c
                    elif 'vales' in val: col_vales = c
                if col_nome and col_vales:
                    header_row = r
                    break

            if col_nome and col_vales and header_row:
                for r in range(header_row + 1, ws.max_row + 1):
                    nome_cell = ws.cell(row=r, column=col_nome).value
                    if nome_cell:
                        norm_excel = normalizar_nome(str(nome_cell))
                        if normalizar_nome(cliente_nome) in norm_excel:
                            ws.cell(row=r, column=col_vales).value = valor_desconto
                            inserido_com_sucesso = True
                            funcionario_encontrado = str(nome_cell)
                            break

        if not inserido_com_sucesso:
            return {"sucesso": False, "erro": f"Cliente '{cliente_nome}' não foi encontrado na planilha base."}

        saida_memoria = io.BytesIO()
        wb.save(saida_memoria)
        saida_memoria.seek(0)

        return StreamingResponse(
            saida_memoria,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=ESCRITORIO_VALES.xlsx", 
                "Access-Control-Expose-Headers": "Content-Disposition, X-Funcionario-Nome",
                "X-Funcionario-Nome": unicodedata.normalize('NFKD', funcionario_encontrado).encode('ASCII', 'ignore').decode('utf-8')
            }
        )
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

@app.post("/api/rpa_farmacia")
async def rpa_farmacia(arquivo_extrato: UploadFile = File(...), arquivo_escritorio: UploadFile = File(...)):
    try:
        conteudo_extrato = await arquivo_extrato.read()
        html_content = conteudo_extrato.decode('utf-8', errors='replace')
        
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html_content, re.IGNORECASE | re.DOTALL)
        dados_farmacia = {}
        
        for row in rows:
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.IGNORECASE | re.DOTALL)
            cleaned_cells = [re.sub(r'<[^>]+>', '', cell).strip().replace('&nbsp;', ' ') for cell in cells]
            
            if len(cleaned_cells) >= 3:
                nome = cleaned_cells[0]
                valor_str = cleaned_cells[2]
                valor_num = valor_str.replace('.', '').replace(',', '.')
                try:
                    float(valor_num)
                    if nome and len(nome) > 3 and "Total" not in nome and "Nome" not in nome:
                        nome_norm = normalizar_nome(nome)
                        dados_farmacia[nome_norm] = valor_str
                except ValueError:
                    pass
        
        if not dados_farmacia:
            return {"sucesso": False, "erro": "Nenhum desconto financeiro foi encontrado no arquivo de extrato enviado."}

        conteudo_escritorio = await arquivo_escritorio.read()
        wb = openpyxl.load_workbook(io.BytesIO(conteudo_escritorio))
        processados = 0
        nao_encontrados = []

        for ws in wb.worksheets:
            col_nome = col_farmacia = header_row = None
            for r in range(1, 15):
                for c in range(1, ws.max_column + 1):
                    val = str(ws.cell(row=r, column=c).value or "").strip().lower()
                    if 'nome' in val and 'colaborador' in val: 
                        col_nome = c
                    elif 'farm' in val or 'convenio' in val or 'farmácia' in val or 'farmacia' in val: 
                        col_farmacia = c
                if col_nome and col_farmacia:
                    header_row = r
                    break

            if col_nome and col_farmacia and header_row:
                for r in range(header_row + 1, ws.max_row + 1):
                    nome_cell = ws.cell(row=r, column=col_nome).value
                    if nome_cell:
                        norm_excel = normalizar_nome(str(nome_cell))
                        for nome_farm, valor in dados_farmacia.items():
                            if nome_farm in norm_excel or norm_excel in nome_farm:
                                ws.cell(row=r, column=col_farmacia).value = valor
                                processados += 1
                                dados_farmacia[nome_farm] = "ENCONTRADO"
                                break

        for nome_farm, status in dados_farmacia.items():
            if status != "ENCONTRADO":
                nao_encontrados.append(nome_farm)

        saida_memoria = io.BytesIO()
        wb.save(saida_memoria)
        saida_memoria.seek(0)

        erros_str = "|".join(nao_encontrados) if nao_encontrados else "Nenhum"
        
        return StreamingResponse(
            saida_memoria,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=ESCRITORIO_FARMACIA.xlsx", 
                "Access-Control-Expose-Headers": "Content-Disposition, X-Processados, X-Nao-Encontrados",
                "X-Processados": str(processados),
                "X-Nao-Encontrados": unicodedata.normalize('NFKD', erros_str).encode('ASCII', 'ignore').decode('utf-8')
            }
        )

    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

@app.post("/api/auditar_folha")
async def auditar_folha(arquivo_pdf: UploadFile = File(...), arquivo_escritorio: UploadFile = File(...)):
    try:
        import pdfplumber
        
        conteudo_escritorio = await arquivo_escritorio.read()
        df_escritorio = pd.read_excel(io.BytesIO(conteudo_escritorio), sheet_name=0)

        col_nome_escritorio = None
        col_faltas_dsr = None

        for col in df_escritorio.columns:
            if 'nome' in str(col).lower() or 'colaborador' in str(col).lower():
                col_nome_escritorio = col
            if 'faltas' in str(col).lower() and 'dsr' in str(col).lower():
                col_faltas_dsr = col

        dados_escritorio = {}
        if col_nome_escritorio and col_faltas_dsr:
            for index, row in df_escritorio.iterrows():
                nome = row[col_nome_escritorio]
                faltas_dsr = row[col_faltas_dsr]
                if pd.notna(nome):
                    norm_name = normalizar_nome(nome)
                    if pd.isna(faltas_dsr):
                        dados_escritorio[norm_name] = {'faltas': 0.0, 'dsr': 0}
                    else:
                        s = str(faltas_dsr).lower().replace('dsr', '').strip()
                        parts = s.split('+')
                        try:
                            f = float(parts[0]) if len(parts) > 0 else 0.0
                            d = int(parts[1]) if len(parts) > 1 else 0
                            dados_escritorio[norm_name] = {'faltas': f, 'dsr': d}
                        except:
                            dados_escritorio[norm_name] = {'faltas': 0.0, 'dsr': 0}

        conteudo_pdf = await arquivo_pdf.read()
        texto_pdf = ""
        with pdfplumber.open(io.BytesIO(conteudo_pdf)) as pdf:
            for page in pdf.pages:
                ext = page.extract_text()
                if ext: texto_pdf += ext + "\n"

        recibos_texto = re.split(r'Total Liquido -->|Total Liquido ->', texto_pdf)
        dados_recibo = {}

        for rt in recibos_texto:
            nome_match = re.search(r'\d{4}\s+([A-ZÇÃÁÉÍÓÚÊ\s]+?)\n', rt)
            if not nome_match:
                 nome_match = re.search(r'\d{4}\s+([A-ZÇÃÁÉÍÓÚÊ\s]{5,})', rt)
                 
            if nome_match:
                nome_cru = nome_match.group(1).strip()
                nome_cru = re.sub(r'LIDER.*|AUXILIAR.*|FAXINEIRA.*|MOTORISTA.*|ENCARREGADO.*|SUPERVISOR.*|ANALISTA.*|ASSISTENTE.*|\d.*', '', nome_cru)
                nome_norm = normalizar_nome(nome_cru.strip())
                
                if len(nome_norm) > 5:
                    faltas = 0.0
                    dsr = 0
                    
                    faltas_match = re.search(r'39[\s\n]*Faltas.*?([\d,]+)', rt, re.IGNORECASE | re.DOTALL)
                    if faltas_match:
                        try: faltas = float(faltas_match.group(1).replace(',', '.'))
                        except: pass
                            
                    dsr_match = re.search(r'103[\s\n]*Faltas\s*DSR.*?([\d,]+)', rt, re.IGNORECASE | re.DOTALL)
                    if dsr_match:
                        try: dsr = int(float(dsr_match.group(1).replace(',', '.')))
                        except: pass
                            
                    if nome_norm in dados_recibo:
                        dados_recibo[nome_norm]['faltas'] = max(faltas, dados_recibo[nome_norm]['faltas'])
                        dados_recibo[nome_norm]['dsr'] = max(dsr, dados_recibo[nome_norm]['dsr'])
                    else:
                        dados_recibo[nome_norm] = {'faltas': faltas, 'dsr': dsr}

        divergencias = []
        for nome_recibo, vals_recibo in dados_recibo.items():
            encontrado = False
            for nome_esc, vals_esc in dados_escritorio.items():
                if nome_recibo in nome_esc or nome_esc in nome_recibo:
                    encontrado = True
                    if vals_recibo['faltas'] != vals_esc['faltas'] or vals_recibo['dsr'] != vals_esc['dsr']:
                        divergencias.append({
                            'nome': nome_recibo,
                            'faltas_escritorio': vals_esc['faltas'],
                            'dsr_escritorio': vals_esc['dsr'],
                            'faltas_recibo': vals_recibo['faltas'],
                            'dsr_recibo': vals_recibo['dsr']
                        })
                    break
                    
        return {
            "sucesso": True,
            "total_auditados": len(dados_recibo),
            "divergencias": divergencias
        }

    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

# ==========================================
# PAINEL GERAL DE INDICADORES (KPIS)
# ==========================================
@app.get("/api/dashboard/kpis")
def obter_kpis_do_banco(mes: int = None, ano: int = None, setor: str = "Todos"):
    hoje = datetime.now()
    mes_int = mes if mes else hoje.month
    ano_int = ano if ano else hoje.year

    inicio_mes_civil = f"{ano_int}-{mes_int:02d}-01"
    ultimo_dia = calendar.monthrange(ano_int, mes_int)[1]
    fim_mes_civil = f"{ano_int}-{mes_int:02d}-{ultimo_dia}"

    if mes_int == 1: mes_anterior, ano_anterior = 12, ano_int - 1
    else: mes_anterior, ano_anterior = mes_int - 1, ano_int
    inicio_mes_fiscal = f"{ano_anterior}-{mes_anterior:02d}-26"
    fim_mes_fiscal = f"{ano_int}-{mes_int:02d}-25"

    todos_colab = ler_do_banco("colaboradores") or []
    todos_deslig = ler_do_banco("desligamentos") or []
    todos_atestados = ler_do_banco("atestados") or []
    todos_adv = ler_do_banco("advertencias") or []
    todos_freq = ler_do_banco("frequencia") or []
    avaliacoes_itens = ler_do_banco("desempenho") or []
    armarios_itens = ler_do_banco("armarios") or []

    vistos_ativos = set()
    ativos_itens = []
    for item in todos_colab:
        props = item.get("properties", {})
        status = extrair_texto(props, "status")
        if status.lower() == "ativo":
            n = normalizar_nome(get_nome_correto(props))
            if n not in vistos_ativos:
                vistos_ativos.add(n)
                ativos_itens.append(item)
                
    setores_atuais = {normalizar_nome(get_nome_correto(i.get("properties", {}))): formatar_setor(extrair_texto(i.get("properties", {}), "setor")) for i in ativos_itens}

    admissoes_itens = [i for i in ativos_itens if inicio_mes_civil <= extrair_texto(i.get("properties", {}), "data")[:10] <= fim_mes_civil]
    
    avaliacoes_filtradas = []
    for item in avaliacoes_itens:
        props = item.get("properties", {})
        dt_aval = extrair_texto(props, "data")
        if dt_aval != "Outros / Não Informado" and len(dt_aval) >= 10 and inicio_mes_civil <= dt_aval[:10] <= fim_mes_civil: 
            avaliacoes_filtradas.append(item)
    avaliacoes_itens = avaliacoes_filtradas
    
    desligamentos_itens = [i for i in todos_deslig if inicio_mes_fiscal <= extrair_texto(i.get("properties", {}), "data")[:10] <= fim_mes_fiscal]
    desligamentos_ano = [i for i in todos_deslig if extrair_texto(i.get("properties", {}), "data")[:4] == str(ano_int)]
    atestados_itens = [i for i in todos_atestados if inicio_mes_fiscal <= extrair_texto(i.get("properties", {}), "data")[:10] <= fim_mes_fiscal]
    
    advertencias_itens = []
    for item in todos_adv:
        props = item.get("properties", {})
        dt = extrair_texto(props, "data")
        if dt != "Outros / Não Informado" and len(dt) >= 10:
            if inicio_mes_fiscal <= dt[:10] <= fim_mes_fiscal:
                advertencias_itens.append(item)

    setores_unicos = set([formatar_setor(extrair_texto(i.get("properties", {}), "setor")) for i in ativos_itens])
    if "Uchoa" in setores_unicos: setores_unicos.remove("Uchoa")
    lista_setores = sorted(list(setores_unicos))

    if setor != "Todos":
        ativos_itens = [i for i in ativos_itens if formatar_setor(extrair_texto(i.get("properties", {}), "setor")) == setor]
        admissoes_itens = [i for i in admissoes_itens if formatar_setor(extrair_texto(i.get("properties", {}), "setor")) == setor]
        desligamentos_itens = [i for i in desligamentos_itens if formatar_setor(extrair_texto(i.get("properties", {}), "setor")) == setor]
        atestados_itens = [i for i in atestados_itens if formatar_setor(extrair_texto(i.get("properties", {}), "setor")) == setor]
        advertencias_itens = [i for i in advertencias_itens if formatar_setor(extrair_texto(i.get("properties", {}), "setor")) == setor]
        desligamentos_ano = [i for i in desligamentos_ano if formatar_setor(extrair_texto(i.get("properties", {}), "setor")) == setor]
        avaliacoes_itens = [i for i in avaliacoes_itens if formatar_setor(extrair_texto(i.get("properties", {}), "setor")) == setor]

    total_ativos = len(ativos_itens)
    dict_perfis = {}
    
    def iniciar_perfil(nome):
        if nome not in dict_perfis:
            dict_perfis[nome] = {"cargo": "-", "setor": "-", "tempo_casa": "-", "salario": 0.0, "historico_atestados": [], "historico_advertencias": [], "faltas_dias": 0.0, "atrasos": 0, "nota_desempenho": 0.0, "qtd_aval": 0}

    alertas_aniversarios, alertas_contratos, alertas_ferias = [], [], []
    for item in ativos_itens:
        props = item.get("properties", {})
        nome = get_nome_correto(props)
        iniciar_perfil(nome)
        dict_perfis[nome]["setor"] = formatar_setor(extrair_texto(props, "setor"))

        adm_str = extrair_texto(props, "data")
        if adm_str != "Outros / Não Informado" and len(adm_str) >= 10:
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
            
        nasc_str = extrair_texto(props, "nascimento")
        if nasc_str != "Outros / Não Informado" and len(nasc_str) >= 10:
            try:
                if int(nasc_str.split("-")[1]) == mes_int: alertas_aniversarios.append({"nome": nome, "dia": int(nasc_str.split("-")[2])})
            except: pass

    alertas_aniversarios = sorted(alertas_aniversarios, key=lambda x: x["dia"])
    alertas_contratos = sorted(alertas_contratos, key=lambda x: x["dia"])
    alertas_ferias = sorted(alertas_ferias, key=lambda x: x["dias_restantes"])

    dict_setores = {}
    for item in atestados_itens:
        s = formatar_setor(extrair_texto(item.get("properties", {}), "setor"))
        if "Uchoa" in s: continue
        if s not in dict_setores: dict_setores[s] = {"setor": s, "atestados": 0, "faltas": 0}
        dict_setores[s]["atestados"] += 1

    total_faltas_inteiras, total_atrasos, total_horas_extras = 0.0, 0, 0.0
    dict_ranking, dict_he_setor = {}, {}
    total_perdas_r = 0.0

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if setor == "Todos": cursor.execute("SELECT nome_funcionario, setor, valor_desconto, faltas_dias FROM historico_folha WHERE mes = ? AND ano = ?", (mes_int, ano_int))
        else: cursor.execute("SELECT nome_funcionario, setor, valor_desconto, faltas_dias FROM historico_folha WHERE mes = ? AND ano = ? COLLATE NOCASE", (mes_int, ano_int))
        for rec in cursor.fetchall():
            nome_f = rec[0]
            nome_norm = normalizar_nome(nome_f)
            
            setor_f = setores_atuais.get(nome_norm, formatar_setor(rec[1]))
            if "Uchoa" in setor_f: continue
            if setor != "Todos" and formatar_setor(setor_f) != formatar_setor(setor): continue
            
            val_desc = rec[2] if rec[2] is not None else 0.0
            faltas_d = rec[3] if rec[3] is not None else 0.0
            total_perdas_r += val_desc
            total_faltas_inteiras += faltas_d
            iniciar_perfil(nome_f)
            dict_perfis[nome_f]["faltas_dias"] += faltas_d
            dict_ranking[nome_f] = dict_ranking.get(nome_f, 0) + faltas_d
            if setor_f not in dict_setores: dict_setores[setor_f] = {"setor": setor_f, "atestados": 0, "faltas": 0}
            dict_setores[setor_f]["faltas"] += faltas_d
        conn.close()
    except Exception as e: pass

    for item in todos_freq:
        props = item.get("properties", {})
        dt = extrair_texto(props, "data")
        if dt != "Outros / Não Informado" and len(dt) >= 10 and inicio_mes_fiscal <= dt[:10] <= fim_mes_fiscal:
            setor_freq = setores_atuais.get(normalizar_nome(get_nome_correto(props)), formatar_setor(extrair_texto(props, "setor")))
            if "Uchoa" in setor_freq: continue
            if setor != "Todos" and formatar_setor(setor_freq) != formatar_setor(setor): continue
            
            nome = get_nome_correto(props)
            iniciar_perfil(nome)
            prop_he = props.get("Horas Extras") or props.get("HE") or props.get("Valor HE") or {}
            qtd_he = prop_he.get("number") if prop_he.get("type") == "number" else 0
            if qtd_he and qtd_he > 0:
                total_horas_extras += qtd_he
                if setor_freq not in dict_he_setor: dict_he_setor[setor_freq] = 0
                dict_he_setor[setor_freq] += qtd_he

    ranking_faltas = sorted([{"nome": k, "faltas": v} for k, v in dict_ranking.items()], key=lambda x: x["faltas"], reverse=True)[:10]
    grafico_he = sorted([{"setor": k, "horas": v} for k, v in dict_he_setor.items()], key=lambda x: x["horas"], reverse=True)
    grafico_setores = list(dict_setores.values())

    dict_ranking_atestados, dict_medicos, dict_cids = {}, {}, {}
    for item in atestados_itens:
        props = item.get("properties", {})
        nome = get_nome_correto(props, is_atestado=True)
        setor_atst = setores_atuais.get(normalizar_nome(nome), formatar_setor(extrair_texto(props, "setor")))
        if "Uchoa" in setor_atst: continue
        
        iniciar_perfil(nome)
        dict_ranking_atestados[nome] = dict_ranking_atestados.get(nome, 0) + 1
        medico = extrair_texto(props, "médico")
        if medico and medico != "Outros / Não Informado": dict_medicos[medico] = dict_medicos.get(medico, 0) + 1
        cid = extrair_texto(props, "cid")
        motivo = extrair_texto(props, "motivo")
        data_str = extrair_texto(props, "data")
        if cid and cid != "Outros / Não Informado":
            label_cid = f"{cid} - {motivo}" if motivo != "Outros / Não Informado" else cid
            dict_cids[label_cid] = dict_cids.get(label_cid, 0) + 1
            dict_perfis[nome]["historico_atestados"].append({"data": data_str[:10] if len(data_str) >= 10 else "-", "motivo": label_cid})
        else:
            dict_perfis[nome]["historico_atestados"].append({"data": data_str[:10] if len(data_str) >= 10 else "-", "motivo": motivo})
    
    ranking_atestados = sorted([{"nome": k, "atestados": v} for k, v in dict_ranking_atestados.items()], key=lambda x: x["atestados"], reverse=True)[:10]
    ranking_medicos = sorted([{"nome": k, "quantidade": v} for k, v in dict_medicos.items()], key=lambda x: x["quantidade"], reverse=True)[:7]
    ranking_cids = sorted([{"nome": k, "quantidade": v} for k, v in dict_cids.items()], key=lambda x: x["quantidade"], reverse=True)[:10]

    dict_adv, dict_ranking_adv = {}, {}
    for item in advertencias_itens:
        props = item.get("properties", {})
        nome = get_nome_correto(props)
        iniciar_perfil(nome)
        
        motivo = extrair_texto(props, "motivo")
        if motivo == "Outros / Não Informado": motivo = extrair_texto(props, "tipo")
        
        titulo_card = ""
        for k, v in props.items():
            if v.get("type") == "title" and v.get("title"):
                titulo_card = v["title"][0]["plain_text"]
                break
                
        texto_busca_atraso = (motivo + " " + titulo_card).lower()
        if "atraso" in texto_busca_atraso or "saída" in texto_busca_atraso or "saida" in texto_busca_atraso:
            total_atrasos += 1
            dict_perfis[nome]["atrasos"] += 1
            
        dict_ranking_adv[nome] = dict_ranking_adv.get(nome, 0) + 1
        dict_adv[motivo] = dict_adv.get(motivo, 0) + 1
        data_str = extrair_texto(props, "data")
        dict_perfis[nome]["historico_advertencias"].append({"data": data_str[:10] if len(data_str) >= 10 else "-", "motivo": motivo})
        
    grafico_advertencias = [{"name": k, "value": v} for k, v in dict_adv.items()]
    ranking_advertencias = sorted([{"nome": k, "advertencias": v} for k, v in dict_ranking_adv.items()], key=lambda x: x["advertencias"], reverse=True)[:10]

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
            
    grafico_radar = [{"subject": c, "A": round(radar_somas[c] / radar_cont[c], 1) if radar_cont[c] > 0 else 0, "fullMark": 5} for c in competencias]

    meses_nomes = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    contagem_meses, dict_motivos = {m: 0 for m in meses_nomes}, {}
    for item in desligamentos_ano:
        props = item.get("properties", {})
        dt = extrair_texto(props, "data")
        if dt != "Outros / Não Informado" and len(dt) >= 10:
            mes_idx = int(dt.split("-")[1]) - 1
            contagem_meses[meses_nomes[mes_idx]] += 1
        motivo = extrair_texto(props, "motivo")
        if motivo not in dict_motivos: dict_motivos[motivo] = 0
        dict_motivos[motivo] += 1
        
    grafico_turnover = [{"mes": mes, "turnover": round((contagem_meses[mes] / total_ativos) * 100, 1) if total_ativos > 0 else 0} for mes in meses_nomes]
    grafico_motivos = [{"name": k, "value": v} for k, v in dict_motivos.items()]

    dict_headcount = {}
    for item in ativos_itens:
        s = formatar_setor(extrair_texto(item.get("properties", {}), "setor"))
        if "Uchoa" in s: continue
        if s not in dict_headcount: dict_headcount[s] = 0
        dict_headcount[s] += 1
    grafico_headcount = sorted([{"setor": k, "quantidade": v} for k, v in dict_headcount.items()], key=lambda x: x["quantidade"], reverse=True)
    turnover_atual = f"{(len(desligamentos_itens) / total_ativos) * 100:.1f}%" if total_ativos > 0 else "0.0%"

    lista_armarios = []
    for item in armarios_itens:
        props = item.get("properties", {})
        
        num_str = "?"
        for k, v in props.items():
            if v.get("type") == "title" and v.get("title"):
                num_str = v["title"][0]["plain_text"]
                break
        
        if num_str == "?":
            n = extrair_texto(props, "armario")
            if n != "Outros / Não Informado": num_str = n
            
        num_val = 0
        try:
             clean_num = ''.join(filter(str.isdigit, num_str))
             num_val = int(clean_num) if clean_num else 0
        except: pass

        dono = get_nome_correto(props)
        if dono == "Outros / Não Informado": dono = None

        status = extrair_texto(props, "status")
        if status == "Outros / Não Informado":
             status = extrair_texto(props, "ocup")
             
        status_clean = "Livre"
        if not status or status == "Outros / Não Informado":
             if dono: status_clean = "Ocupado"
             else: status_clean = "Livre"
        else:
            status_lower = status.lower()
            if "ocup" in status_lower: status_clean = "Ocupado"
            elif "manuten" in status_lower or "indispon" in status_lower: status_clean = "Manutenção"
            elif "livre" in status_lower or "dispon" in status_lower: status_clean = "Livre"
            
        if dono and setor != "Todos":
             dono_norm = normalizar_nome(dono)
             setor_dono = setores_atuais.get(dono_norm, "Outros")
             if formatar_setor(setor_dono) != formatar_setor(setor):
                 continue
                 
        lista_armarios.append({"num": num_str if num_str != "Outros / Não Informado" else "?", "sort_val": num_val, "dono": dono, "status": status_clean})

    lista_armarios = sorted(lista_armarios, key=lambda x: x["sort_val"])

    return {
        "funcionarios": total_ativos, "admissoes": len(admissoes_itens), "desligamentos": len(desligamentos_itens), "turnover": turnover_atual,     
        "atestados": len(atestados_itens), "advertencias": len(advertencias_itens), 
        "faltas": total_faltas_inteiras, "atrasos": total_atrasos,
        "custo_absenteismo": total_perdas_r, "avaliacoes": len(avaliacoes_itens),
        "graficoSetores": grafico_setores, "graficoTurnover": grafico_turnover, "graficoMotivos": grafico_motivos, "graficoHeadcount": grafico_headcount,
        "alertasAniversarios": alertas_aniversarios, "alertasContratos": alertas_contratos,
        "graficoAdvertencias": grafico_advertencias, 
        "rankingFaltas": ranking_faltas, 
        "rankingAtestados": ranking_atestados, 
        "rankingAdvertencias": ranking_advertencias,
        "rankingMedicos": ranking_medicos, "rankingCids": ranking_cids,       
        "graficoRadar": grafico_radar, "perfis360": dict_perfis,
        "alertasFerias": alertas_ferias, "totalHorasExtras": total_horas_extras, "graficoHorasExtras": grafico_he,
        "armarios": lista_armarios, "setoresDisponiveis": lista_setores
    }
from .config import RULES
from fastapi import APIRouter
from .core import File, UploadFile, io, normalizar_nome, openpyxl, pd, re

router = APIRouter()

@router.post("/api/auditar_folha")
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


@router.post("/api/auditar_bonus_universal")
async def auditar_bonus_universal(arquivo_sap: UploadFile = File(...), arquivo_planilha: UploadFile = File(...)):
    try:
        import pdfplumber
        import io
        
        # 1. LER A PLANILHA DE BÔNUS JÁ PREENCHIDA
        conteudo_bonus = await arquivo_planilha.read()
        wb = openpyxl.load_workbook(io.BytesIO(conteudo_bonus), data_only=True)
        ws = wb.worksheets[0]

        col_nome = col_desconto = header_row = None
        for r in range(1, 25):
            for c in range(1, ws.max_column + 1):
                val = str(ws.cell(row=r, column=c).value or "").strip().lower()
                if 'nome' in val and 'colaborador' in val: col_nome = c
                elif 'desconto' in val and '%' in val: col_desconto = c
            if col_nome and col_desconto:
                header_row = r
                break

        dados_planilha = {}
        if col_nome and col_desconto and header_row:
            for r in range(header_row + 1, ws.max_row + 1):
                nome_cell = ws.cell(row=r, column=col_nome).value
                if pd.notna(nome_cell) and str(nome_cell).strip() != "":
                    norm_name = normalizar_nome(str(nome_cell))
                    desc = ws.cell(row=r, column=col_desconto).value
                    try: desc = float(desc)
                    except: desc = 0.0
                    dados_planilha[norm_name] = {'desconto': desc}

        # 2. LER O ESPELHO DE PONTO SAP (Pode ser PDF de Uchôa ou XLS de Ibirá!)
        conteudo_sap = await arquivo_sap.read()
        filename = arquivo_sap.filename.lower()
        dados_sap = {}

        if filename.endswith(".pdf"):
            texto_pdf = ""
            with pdfplumber.open(io.BytesIO(conteudo_sap)) as pdf:
                for page in pdf.pages:
                    ext = page.extract_text()
                    if ext: texto_pdf += ext + "\n"

            espelhos = re.split(r'ESPELHO DO CARTÃO DE PONTO', texto_pdf)[1:]

            for e in espelhos:
                nome_match = re.search(r'Reconheço a exatidão destas informações e dou fé,\n*([^\n]+)', e)
                if not nome_match: continue
                     
                nome_norm = normalizar_nome(nome_match.group(1).strip())
                
                faltas_integrais = 0
                meio_periodo = 0
                atestados = 0
                
                linhas = e.split('\n')
                for linha in linhas:
                    if re.search(r'^(Seg|Ter|Qua|Qui|Sex|Sab|Dom)\s+\d{2}/\d{2}', linha.strip()):
                        fc = linha.count('FALTA')
                        if fc >= 3: faltas_integrais += 1
                        elif 0 < fc <= 2: meio_periodo += 1
                        
                        mc = linha.count('MEDIC') + linha.count('ATEST')
                        if mc >= 3: atestados += 1
                        elif 0 < mc <= 2: atestados += 0.5 

                desc_esperado = min(1.0, (faltas_integrais * 1.0) + (meio_periodo * float(RULES.get("bonus_meio_periodo", 0.25))) + (atestados * float(RULES.get("bonus_atestado", 0.5))))
                dados_sap[nome_norm] = {
                    'faltas': faltas_integrais, 'meios': meio_periodo, 'atestados': atestados, 'desconto_esperado': desc_esperado
                }
                
        else:
            # É arquivo Excel (.xls ou .xlsx)
            engine_type = 'xlrd' if filename.endswith('.xls') else 'openpyxl'
            df_sap = pd.read_excel(io.BytesIO(conteudo_sap), header=None, engine=engine_type)
            current_norm = None
            
            for i, row in df_sap.iterrows():
                row_str = ' | '.join([str(x).strip() if pd.notna(x) else "" for x in row.values])
                
                if 'Funcionário' in row_str and ':' in row_str:
                    parts = row_str.split(':')
                    if len(parts) > 1:
                        emp_parts = parts[1].replace('|', '').strip().split(' ', 1)
                        if len(emp_parts) == 2:
                            current_norm = normalizar_nome(emp_parts[1])
                            if current_norm not in dados_sap:
                                dados_sap[current_norm] = {'faltas': 0, 'meios': 0, 'atestados': 0, 'desconto_esperado': 0.0}
                        else:
                            current_norm = None
                            
                if current_norm:
                    vals = []
                    for j in [4, 5, 6, 7]: 
                        if j < len(row.values) and pd.notna(row.values[j]) and str(row.values[j]).strip() != "":
                            vals.append(str(row.values[j]).strip().upper())
                    
                    fc = sum(1 for v in vals if 'FALTA' in v)
                    mc = sum(1 for v in vals if 'MEDIC' in v or 'ATEST' in v)
                    
                    if fc >= 3: dados_sap[current_norm]['faltas'] += 1
                    elif 0 < fc <= 2: dados_sap[current_norm]['meios'] += 1
                        
                    if mc >= 3: dados_sap[current_norm]['atestados'] += 1
                    elif 0 < mc <= 2: dados_sap[current_norm]['atestados'] += 0.5
            
            for nome, info in dados_sap.items():
                info['desconto_esperado'] = min(1.0, (info['faltas'] * 1.0) + (info['meios'] * float(RULES.get('bonus_meio_periodo', 0.25))) + (info['atestados'] * float(RULES.get('bonus_atestado', 0.5))))

        # 3. CRUZAR DADOS E GERAR RELATÓRIO DE DIVERGÊNCIAS
        divergencias = []
        for nome_sap, vals_sap in dados_sap.items():
            encontrado = False
            for nome_plan, vals_plan in dados_planilha.items():
                if nome_sap in nome_plan or nome_plan in nome_sap:
                    encontrado = True
                else:
                    p_sap = nome_sap.split()
                    p_plan = nome_plan.split()
                    if p_sap and p_plan and p_sap[0] == p_plan[0]:
                        comuns = set(p_sap).intersection(set(p_plan))
                        tamanho_menor = min(len(p_sap), len(p_plan))
                        if len(comuns) >= 2 and len(comuns) >= (tamanho_menor - 1):
                            encontrado = True
                            
                if encontrado:
                    if round(vals_sap['desconto_esperado'], 2) != round(vals_plan['desconto'], 2):
                        divergencias.append({
                            'nome': nome_sap,
                            'desc_planilha': f"{int(vals_plan['desconto']*100)}%",
                            'desc_pdf': f"{int(vals_sap['desconto_esperado']*100)}%",
                            'detalhes_pdf': f"{vals_sap['faltas']} Faltas | {vals_sap['meios']} Meios | {vals_sap['atestados']} Atestados"
                        })
                    break
                    
        return {
            "sucesso": True,
            "total_auditados": len(dados_sap),
            "divergencias": divergencias
        }

    except Exception as e:
        return {"sucesso": False, "erro": str(e)}


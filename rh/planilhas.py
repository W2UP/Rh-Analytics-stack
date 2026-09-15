from .config import RULES
from .rules import match_name
from fastapi import APIRouter
from .core import File, Form, StreamingResponse, UploadFile, io, normalizar_nome, openpyxl, pd, re, somar_horas, unicodedata

router = APIRouter()

@router.post("/api/rpa_horas_extras")
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
                        nome_encontrado_dict = match_name(norm_excel, dados_ativos)
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


@router.post("/api/rpa_bonus")
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
                    dados_bonus[current_norm]["desconto"] += float(RULES.get("bonus_meio_periodo", 0.25)) # 25% de desconto
                    dados_bonus[current_norm]["motivos"].append("Meio Período Falta (25%)")
                    
                if mc >= 3:
                    dados_bonus[current_norm]["desconto"] += float(RULES.get("bonus_atestado", 0.5)) # 50% de desconto
                    dados_bonus[current_norm]["motivos"].append("Atestado (50%)")
                elif 0 < mc <= 2:
                    dados_bonus[current_norm]["desconto"] += float(RULES.get("bonus_meio_periodo", 0.25)) # 25% de desconto
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
                        
                        nome_encontrado_dict = match_name(norm_excel, dados_bonus)
                        # --- FIM DA BUSCA INTELIGENTE DE NOMES ---
                        
                        # Se achou a pessoa e ela TEVE falta/atestado, aplica o desconto
                        if nome_encontrado_dict and dados_bonus[nome_encontrado_dict]["desconto"] > 0:
                            info = dados_bonus[nome_encontrado_dict]
                            
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
                            
                        # Se a pessoa existe na planilha mas NÃO TEVE falta/atestado no SAP
                        else:
                            # Preenche explicitamente com 0 para a fórmula do Excel manter 100% do bônus!
                            ws.cell(row=r, column=col_desconto).value = 0
                            if col_motivo:
                                ws.cell(row=r, column=col_motivo).value = ""

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


@router.post("/api/extrair_vales")
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


@router.post("/api/injetar_vales")
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


@router.post("/api/rpa_farmacia")
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
                        nome_farm = match_name(norm_excel, dados_farmacia)
                        if nome_farm and dados_farmacia[nome_farm] != "ENCONTRADO":
                            ws.cell(row=r, column=col_farmacia).value = dados_farmacia[nome_farm]
                            processados += 1
                            dados_farmacia[nome_farm] = "ENCONTRADO"

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


from .identity import EmployeeIndex
from .rules import money, excluded_sector
from fastapi import APIRouter
from .core import File, RULES, UploadFile, extrair_texto, formatar_setor, get_nome_correto, io, ler_do_banco, normalizar_nome, pd, re, validar_nomes_importacao

router = APIRouter()

@router.post("/api/processar_ponto")
async def processar_arquivo_ponto(arquivo: UploadFile = File(...)):
    try:
        conteudo = await arquivo.read()
        try: df = pd.read_excel(io.BytesIO(conteudo), header=None, engine='xlrd')
        except Exception as e: return {"sucesso": False, "erro": f"Erro Técnico do Python: {str(e)}"}
        colabs = ler_do_banco("colaboradores") or []
        index = EmployeeIndex(colabs)
        dict_salarios = {}
        for c in colabs:
            props = c.get("properties", {})
            nome = get_nome_correto(props)
            sal_str = extrair_texto(props, "Salário (R$)")
            salario = 0.0
            try: salario = money(sal_str)
            except: pass
            setor = extrair_texto(props, "Setor")
            nome_norm = normalizar_nome(nome)
            dict_salarios[c["id"]] = {"salario": salario, "setor": setor, "nome_original": nome}

        resultados = []
        nome_atual_sap = None
        setor_atual_sap = None
        faltas_dias_atual = 0.0
        
        nomes_ignorados = RULES.get("nomes_ignorados_ponto", [])
        
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
                        else: nome_atual_sap = index.find(emp_parts[0], emp_parts[1])["id"]
                        setor_atual_sap = None 
                        faltas_dias_atual = 0.0
                        
            if 'Setor' in row_str and ':' in row_str:
                parts = row_str.split(':')
                if len(parts) > 1:
                    sector_name_parts = parts[1].split('|')
                    found = [s.strip() for s in sector_name_parts if s.strip() and not s.strip().isdigit()]
                    if found: setor_atual_sap = formatar_setor(found[0])
            if setor_atual_sap and excluded_sector(setor_atual_sap):
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
                            if salario <= 0: raise ValueError("Salário ausente ou inválido. Corrija o cadastro antes de processar a folha.") 
                            valor_hora = salario / float(RULES.get("divisor_horas_mensais", 220))
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
                    except ValueError as erro: return {"sucesso": False, "erro": str(erro)}
                    nome_atual_sap = None 

        return {"sucesso": True, "processados": len(resultados), "dados": resultados}
    except Exception as e: return {"sucesso": False, "erro": str(e)}


@router.post("/api/dashboard_tempo_real")
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
        validar_nomes_importacao(colabs)
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


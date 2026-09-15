from .rules import excluded_sector
from fastapi import APIRouter
from .core import DB_PATH, Query, RULES, calendar, datetime, extrair_texto, field, formatar_setor, get_nome_correto, ler_do_banco, logging, normalizar_nome, sqlite3, summarize, sync, timedelta

router = APIRouter()

@router.get("/api/dashboard/kpis")
def obter_kpis_do_banco(mes: int | None = Query(default=None, ge=1, le=12), ano: int | None = Query(default=None, ge=2000, le=2100), setor: str = "Todos"):
    hoje = datetime.now()
    mes_int = mes if mes else hoje.month
    ano_int = ano if ano else hoje.year

    inicio_mes_civil = f"{ano_int}-{mes_int:02d}-01"
    ultimo_dia = calendar.monthrange(ano_int, mes_int)[1]
    fim_mes_civil = f"{ano_int}-{mes_int:02d}-{ultimo_dia}"

    if mes_int == 1: mes_anterior, ano_anterior = 12, ano_int - 1
    else: mes_anterior, ano_anterior = mes_int - 1, ano_int
    
    # Seus novos dias de corte fiscal
    inicio_mes_fiscal = f"{ano_anterior}-{mes_anterior:02d}-25"
    fim_mes_fiscal = f"{ano_int}-{mes_int:02d}-24"

    # Criando o texto da competência
    meses_pt = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
    texto_competencia = f"25 de {meses_pt[mes_anterior]} de {ano_anterior} a 24 de {meses_pt[mes_int]} de {ano_int}"

    todos_colab = ler_do_banco("colaboradores") or []
    todos_deslig = ler_do_banco("desligamentos") or []
    todos_atestados = ler_do_banco("atestados") or []
    todos_adv = ler_do_banco("advertencias") or []
    todos_freq = ler_do_banco("frequencia") or []
    avaliacoes_itens = ler_do_banco("desempenho") or []
    armarios_itens = ler_do_banco("armarios") or []

    apuracao = summarize(todos_colab, todos_deslig, mes_int, ano_int, setor)
    ativos_itens = apuracao["ativos"]
    setores_atuais = {normalizar_nome(get_nome_correto(i.get("properties", {}))): formatar_setor(extrair_texto(i.get("properties", {}), "setor")) for i in ativos_itens}
    admissoes_itens = apuracao["admissoes_itens"]

    avaliacoes_filtradas = []
    for item in avaliacoes_itens:
        props = item.get("properties", {})
        dt_aval = field(item, "Data da Avaliação")
        if dt_aval != "Outros / Não Informado" and len(dt_aval) >= 10 and inicio_mes_fiscal <= dt_aval[:10] <= fim_mes_fiscal: 
            avaliacoes_filtradas.append(item)
    avaliacoes_itens = avaliacoes_filtradas
    
    desligamentos_itens = apuracao["desligamentos_itens"]
    desligamentos_ano = [i for i in todos_deslig if field(i, "Data de Desligamento")[:4] == str(ano_int)]
    atestados_itens = [i for i in todos_atestados if inicio_mes_fiscal <= field(i, "Data de Entrega")[:10] <= fim_mes_fiscal]
    
    advertencias_itens = []
    for item in todos_adv:
        props = item.get("properties", {})
        dt = field(item, "Data da Advertência")
        if dt and len(dt) >= 10:
            if inicio_mes_fiscal <= dt[:10] <= fim_mes_fiscal:
                advertencias_itens.append(item)

    setores_unicos = set([formatar_setor(field(i, "Setor")) for i in todos_colab + todos_deslig if field(i, "Setor")])
    setores_unicos -= set(RULES.get("setores_excluidos", ["Uchoa"]))
    lista_setores = sorted(list(setores_unicos))

    if setor != "Todos":
        ativos_itens = [i for i in ativos_itens if formatar_setor(extrair_texto(i.get("properties", {}), "setor")) == setor]
        admissoes_itens = [i for i in admissoes_itens if formatar_setor(extrair_texto(i.get("properties", {}), "setor")) == setor]
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

        adm_str = extrair_texto(props, "Data de admissão")
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
        if excluded_sector(s): continue
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
            if excluded_sector(setor_f): continue
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
    except Exception:
        logging.exception("Falha ao calcular dados de folha")

    for item in todos_freq:
        props = item.get("properties", {})
        dt = extrair_texto(props, "data")
        if dt != "Outros / Não Informado" and len(dt) >= 10 and inicio_mes_fiscal <= dt[:10] <= fim_mes_fiscal:
            setor_freq = setores_atuais.get(normalizar_nome(get_nome_correto(props)), formatar_setor(extrair_texto(props, "setor")))
            if excluded_sector(setor_freq): continue
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
        if excluded_sector(setor_atst): continue
        
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
        
    grafico_turnover = []
    for numero, nome_mes in enumerate(meses_nomes, 1):
        dados_mes = summarize(todos_colab, todos_deslig, numero, ano_int, setor)
        grafico_turnover.append({"mes": nome_mes, "turnover": dados_mes["turnover_valor"]})
    grafico_motivos = [{"name": k, "value": v} for k, v in dict_motivos.items()]

    dict_headcount = {}
    for item in ativos_itens:
        s = formatar_setor(extrair_texto(item.get("properties", {}), "setor"))
        if excluded_sector(s): continue
        if s not in dict_headcount: dict_headcount[s] = 0
        dict_headcount[s] += 1
    grafico_headcount = sorted([{"setor": k, "quantidade": v} for k, v in dict_headcount.items()], key=lambda x: x["quantidade"], reverse=True)
    turnover_atual = apuracao["turnover"]
    anterior_mes, anterior_ano = (12, ano_int - 1) if mes_int == 1 else (mes_int - 1, ano_int)
    anterior = summarize(todos_colab, todos_deslig, anterior_mes, anterior_ano, setor)
    comparacao = {k: apuracao[k] - anterior[k] for k in ("funcionarios", "admissoes", "desligamentos")}
    dict_motivos = {}
    for item in desligamentos_itens:
        motivo = field(item, "Motivo de Desligamento") or "Não informado"
        dict_motivos[motivo] = dict_motivos.get(motivo, 0) + 1
    grafico_motivos = [{"name": k, "value": v} for k,v in dict_motivos.items()]

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
        "armarios": lista_armarios, "setoresDisponiveis": lista_setores,
        "periodo_fiscal": texto_competencia,
        "detalhes": apuracao["detalhes"], "avisos": apuracao["avisos"],
        "base_turnover": apuracao["base_turnover"], "comparacao": comparacao,
        "sincronizacao": sync.status()
    }


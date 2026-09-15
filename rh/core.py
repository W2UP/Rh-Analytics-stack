from fastapi import FastAPI, BackgroundTasks, UploadFile, File, Form, Request, Query, HTTPException

from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import StreamingResponse

from pydantic import BaseModel

import requests

from datetime import datetime, timedelta 

import calendar 

import logging

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

from rh.config import DB_PATH, NOTION_TOKEN, ORIGINS, RULES

from rh.security import guard, init_security, router as auth_router

from rh import sync

from rh.payroll import init_payroll, router as payroll_router

from rh.metrics import summarize, period, field, parsed, norm

logging.basicConfig(level=logging.INFO)

DB_COLABORADORES = "3ba2051d7a6b8005b98af9fab951026d"

DB_DESLIGAMENTOS = "3ab2051d7a6b808bb0d8fe4199cd5ed9"

DB_ATESTADOS = "ec42d14b9f4243a4ae42a4e704396b1c"

DB_ADVERTENCIAS = "3982051d7a6b8012b894f48c52cdab79"

DB_FREQUENCIA = "39d2051d7a6b805cac20cb52b5c0b476"

DB_DESEMPENHO = "14378c804c6643a3864e72d7947c822f"

DB_ARMARIOS = "3862051d7a6b80f9848adf9e0d50c944"

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

def salvar_no_banco(tabela_nome, dados_lista):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    json_str = json.dumps(dados_lista)
    agora = datetime.now().isoformat()
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

buscar_itens_notion = sync.fetch_database

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

DATABASES = {"colaboradores": DB_COLABORADORES, "desligamentos": DB_DESLIGAMENTOS, "atestados": DB_ATESTADOS, "advertencias": DB_ADVERTENCIAS, "frequencia": DB_FREQUENCIA, "desempenho": DB_DESEMPENHO, "armarios": DB_ARMARIOS}

def validar_nomes_importacao(colabs):
    vistos = set()
    for item in colabs:
        nome = normalizar_nome(get_nome_correto(item.get("properties", {})))
        if nome and nome in vistos:
            raise ValueError("Existem nomes repetidos na base. Vincule os registros por matrícula antes de importar arquivos para evitar misturar colaboradores.")
        vistos.add(nome)

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


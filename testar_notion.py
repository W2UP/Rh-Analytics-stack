import requests
import json

# ==========================================
# 🛑 COLE SUAS CHAVES AQUI DENTRO DAS ASPAS
# ==========================================
NOTION_TOKEN = "ntn_b86757525552BOl8M9h0NsNEntm9aZiTiVxCiwkNa8Kdue"
DATABASE_ID = "3ba2051d7a6b8005b98af9fab951026d"

# Configuração de autorização do Notion
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# Endereço oficial da API do Notion para consultar bancos de dados
url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

print("⏳ Conectando ao Notion, aguarde...")

# Fazendo a pergunta (requisição) para o Notion
response = requests.post(url, headers=headers)

if response.status_code == 200:
    dados = response.json()
    total_funcionarios = len(dados["results"])
    print("✅ SUCESSO! A conexão com o Notion funcionou perfeitamente!")
    print(f"👥 O Python encontrou {total_funcionarios} funcionários cadastrados nessa tabela.")
else:
    print("❌ Ops, algo deu errado.")
    print(f"Código do erro: {response.status_code}")
    print(response.text)
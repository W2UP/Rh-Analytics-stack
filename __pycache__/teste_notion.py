import requests
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

NOTION_TOKEN = "ntn_b86757525552BOl8M9h0NsNEntm9aZiTiVxCiwkNa8Kdue"
DB_ARMARIOS = "3872051d7a6b80c2b69ceb5e4db649cb"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

url = f"https://api.notion.com/v1/databases/{DB_ARMARIOS}/query"

print("📡 Conectando ao Notion...")
response = requests.post(url, headers=headers, verify=False)

if response.status_code == 200:
    dados = response.json()
    itens = dados.get("results", [])
    print(f"✅ Sucesso! Encontrei {len(itens)} armários.")
    
    if len(itens) > 0:
        print("\n🔎 Estrutura do primeiro armário encontrado:")
        # Imprime bonito no terminal para investigarmos
        print(json.dumps(itens[0].get("properties", {}), indent=2, ensure_ascii=False))
else:
    print(f"❌ Erro ao conectar: {response.status_code}")
    print(response.text)
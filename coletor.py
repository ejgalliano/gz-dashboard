import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Carregar credenciais
load_dotenv()
META_TOKEN = os.getenv("META_ACCESS_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Headers para o Supabase (REST API direta)
headers_supabase = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def salvar_no_supabase(tabela, dados):
    url = f"{SUPABASE_URL}/rest/v1/{tabela}"
    response = requests.post(url, json=dados, headers=headers_supabase)
    return response

def buscar_clientes():
    url = f"{SUPABASE_URL}/rest/v1/clientes"
    print(f"URL chamada: {url}")
    response = requests.get(url, headers=headers_supabase)
    print(f"Status: {response.status_code}")
    print(f"Resposta: {response.text}")
    return response.json()

def coletar_metricas_meta(account_id, cliente_id):
    ontem = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    url = f"https://graph.facebook.com/v20.0/{account_id}/insights"
    params = {
        "access_token": META_TOKEN,
        "fields": "spend,impressions,clicks,actions,action_values",
        "time_range": f'{{"since":"{ontem}","until":"{ontem}"}}',
        "level": "account"
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if "error" in data:
        print(f"❌ Erro na conta {account_id}: {data['error']['message']}")
        return
    
    if not data.get("data"):
        print(f"⚠️ Sem dados para {account_id} em {ontem}")
        return
    
    d = data["data"][0]
    
    conversoes = 0
    receita = 0.0
    for action in d.get("actions", []):
        if action["action_type"] == "purchase":
            conversoes = int(float(action["value"]))
    for av in d.get("action_values", []):
        if av["action_type"] == "purchase":
            receita = float(av["value"])
    
    gasto = float(d.get("spend", 0))
    impressoes = int(d.get("impressions", 0))
    cliques = int(d.get("clicks", 0))
    ctr = cliques / impressoes if impressoes > 0 else 0
    cpa = gasto / conversoes if conversoes > 0 else 0
    roas = receita / gasto if gasto > 0 else 0
    
    salvar_no_supabase("metricas_diarias", {
        "cliente_id": cliente_id,
        "data": ontem,
        "gasto": gasto,
        "impressoes": impressoes,
        "cliques": cliques,
        "conversoes": conversoes,
        "receita": receita,
        "cpa": cpa,
        "ctr": ctr,
        "roas": roas
    })
    
    print(f"✅ {account_id} | Gasto: R${gasto:.2f} | Cliques: {cliques} | Conv: {conversoes} | ROAS: {roas:.2f}")

# Executar coleta
clientes = buscar_clientes()
if isinstance(clientes, list):
    print(f"Coletando dados de {len(clientes)} clientes...")
    for cliente in clientes:
        coletar_metricas_meta(cliente["account_id"], cliente["id"])
    print("Coleta finalizada!")
else:
    print(f"Erro ao buscar clientes: {clientes}")
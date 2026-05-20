import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
META_TOKEN = os.getenv("META_ACCESS_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

headers_supabase = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

def get(url, params=None):
    if params is None:
        params = {}
    params["access_token"] = META_TOKEN
    r = requests.get(url, params=params)
    return r.json()

def salvar(tabela, dados):
    url = f"{SUPABASE_URL}/rest/v1/{tabela}"
    r = requests.post(url, json=dados, headers=headers_supabase)
    if r.status_code not in [200, 201]:
        print(f"  Erro ao salvar em {tabela}: {r.text}")

def buscar_clientes():
    url = f"{SUPABASE_URL}/rest/v1/clientes"
    r = requests.get(url, headers={**headers_supabase, "Prefer": ""}, params={"ativo": "eq.true", "select": "*"})
    return r.json()

def extrair_action(data, action_type):
    for a in data.get("actions", []):
        if a["action_type"] == action_type:
            return float(a["value"])
    return 0.0

def extrair_action_value(data, action_type):
    for a in data.get("action_values", []):
        if a["action_type"] == action_type:
            return float(a["value"])
    return 0.0

def coletar_saldo(account_id, cliente_id):
    BASE = "https://graph.facebook.com/v20.0"

    r = get(f"{BASE}/{account_id}", {"fields": "balance,amount_spent,currency,spend_cap"})
    balance = float(r.get("balance", 0)) / 100
    amount_spent = float(r.get("amount_spent", 0)) / 100
    currency = r.get("currency", "BRL")

    rc = get(f"{BASE}/{account_id}/campaigns", {
        "fields": "name,daily_budget,lifetime_budget,status,effective_status",
        "filtering": '[{"field":"effective_status","operator":"IN","value":["ACTIVE"]}]',
        "limit": 100
    })
    campanhas = rc.get("data", [])
    orcamento_diario = sum(
        float(c.get("daily_budget", 0)) / 100
        for c in campanhas
        if c.get("daily_budget")
    )

    hoje = datetime.now().strftime("%Y-%m-%d")
    sete_dias = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    ri = get(f"{BASE}/{account_id}/insights", {
        "fields": "spend",
        "time_range": f'{{"since":"{sete_dias}","until":"{hoje}"}}',
        "level": "account"
    })
    gasto_7d = sum(float(d.get("spend", 0)) for d in ri.get("data", []))

    media_diaria = gasto_7d / 7 if gasto_7d > 0 else orcamento_diario
    dias_restantes = round(balance / media_diaria, 1) if media_diaria > 0 else None

    salvar("account_balance", {
        "cliente_id": cliente_id,
        "account_id": account_id,
        "balance": balance,
        "amount_spent": amount_spent,
        "currency": currency,
        "orcamento_diario_ativo": orcamento_diario,
        "gasto_7d": gasto_7d,
        "media_diaria_7d": round(media_diaria, 2),
        "dias_restantes": dias_restantes,
        "campanhas_ativas": len(campanhas),
        "coletado_em": datetime.now().isoformat()
    })

    print(f"  💰 Saldo: R${balance:.2f} | Orç. diário: R${orcamento_diario:.2f} | Dias restantes: {dias_restantes}")
    return balance, orcamento_diario, media_diaria

def coletar_metricas(account_id, cliente_id):
    BASE = "https://graph.facebook.com/v20.0"
    ontem = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    r = get(f"{BASE}/{account_id}/insights", {
        "fields": "spend,impressions,reach,frequency,clicks,ctr,cpc,cpm,actions,action_values,cost_per_action_type",
        "time_range": f'{{"since":"{ontem}","until":"{ontem}"}}',
        "level": "account"
    })

    if "error" in r:
        print(f"  ❌ Erro API: {r['error']['message']}")
        return

    if not r.get("data"):
        print(f"  ⚠️ Sem dados para {ontem}")
        return

    d = r["data"][0]

    gasto      = float(d.get("spend", 0))
    impressoes = int(d.get("impressions", 0))
    alcance    = int(d.get("reach", 0))
    frequencia = float(d.get("frequency", 0))
    cliques    = int(d.get("clicks", 0))
    ctr        = float(d.get("ctr", 0)) / 100
    cpc        = float(d.get("cpc", 0))
    cpm        = float(d.get("cpm", 0))

    compras       = extrair_action(d, "purchase")
    valor_compras = extrair_action_value(d, "purchase")
    leads         = extrair_action(d, "lead")

    roas = valor_compras / gasto if gasto > 0 else 0
    cpa  = gasto / compras if compras > 0 else 0
    cpl  = gasto / leads if leads > 0 else 0

    salvar("metricas_diarias", {
        "cliente_id": cliente_id,
        "data": ontem,
        "gasto": gasto,
        "impressoes": impressoes,
        "alcance": alcance,
        "frequencia": frequencia,
        "cliques": cliques,
        "conversoes": int(compras),
        "receita": valor_compras,
        "leads": int(leads),
        "cpa": cpa,
        "cpl": cpl,
        "cpc": cpc,
        "cpm": cpm,
        "ctr": ctr,
        "roas": roas
    })

    print(f"  📊 Gasto: R${gasto:.2f} | Alcance: {alcance:,} | CTR: {ctr*100:.2f}% | CPC: R${cpc:.2f} | Conv: {int(compras)} | Leads: {int(leads)}")

# === MAIN ===
clientes = buscar_clientes()
if not isinstance(clientes, list):
    print(f"Erro ao buscar clientes: {clientes}")
    exit()

print(f"\n🚀 Coletando {len(clientes)} clientes...\n")
for c in clientes:
    print(f"▶ {c['nome']} ({c['account_id']})")
    if c["plataforma"] in ["meta", "ambos"]:
        coletar_saldo(c["account_id"], c["id"])
        coletar_metricas(c["account_id"], c["id"])
    print()

print("✅ Coleta finalizada!")
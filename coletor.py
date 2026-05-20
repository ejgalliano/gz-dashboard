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

BASE = "https://graph.facebook.com/v20.0"

def api_get(endpoint, params=None):
    if params is None:
        params = {}
    params["access_token"] = META_TOKEN
    r = requests.get(f"{BASE}/{endpoint}", params=params)
    return r.json()

def salvar(tabela, dados):
    url_base = f"{SUPABASE_URL}/rest/v1/{tabela}"
    
    # Para metricas_campanhas, deleta antes de inserir para evitar duplicata
    if tabela == "metricas_campanhas":
        del_url = f"{url_base}?campaign_id=eq.{dados['campaign_id']}&data=eq.{dados['data']}"
        requests.delete(del_url, headers=headers_supabase)
    
    r = requests.post(url_base, json=dados, headers=headers_supabase)
    if r.status_code not in [200, 201]:
        print(f"  ⚠️ Erro ao salvar em {tabela}: {r.text[:200]}")

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
    # Saldo da conta
    r = api_get(account_id, {"fields": "balance,amount_spent,currency"})
    balance = float(r.get("balance", 0)) / 100
    amount_spent = float(r.get("amount_spent", 0)) / 100
    currency = r.get("currency", "BRL")

    # Campanhas ativas
    rc = api_get(f"{account_id}/campaigns", {
        "fields": "id,name,daily_budget,effective_status",
        "filtering": '[{"field":"effective_status","operator":"IN","value":["ACTIVE"]},{"field":"impressions","operator":"GREATER_THAN","value":"0"}]',
        "limit": 100
    })
    campanhas = rc.get("data", [])
    orcamento_diario = sum(
        float(c.get("daily_budget", 0)) / 100
        for c in campanhas if c.get("daily_budget")
    )

    # Gasto últimos 7 dias
    hoje = datetime.now().strftime("%Y-%m-%d")
    sete_dias = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    ri = api_get(f"{account_id}/insights", {
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

    print(f"  💰 Saldo: R${balance:.2f} | Campanhas ativas: {len(campanhas)} | Dias restantes: {dias_restantes}")
    return campanhas

def coletar_metricas_campanhas(account_id, cliente_id, campanhas_ativas):
    """Coleta métricas no nível de campanha — apenas campanhas ativas com alcance > 0"""
    ontem = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    r = api_get(f"{account_id}/insights", {
        "fields": "campaign_id,campaign_name,spend,impressions,reach,frequency,clicks,ctr,cpc,cpm,actions,action_values",
        "time_range": f'{{"since":"{ontem}","until":"{ontem}"}}',
        "level": "campaign",
        "limit": 100
    })

    if "error" in r:
        print(f"  ❌ Erro API: {r['error']['message']}")
        return [], {}

    campanhas_data = r.get("data", [])
    ids_ativas = {c["id"] for c in campanhas_ativas}

    total_gasto = 0
    total_alcance = 0
    total_cliques = 0
    total_impressoes = 0
    total_compras = 0
    total_receita = 0
    total_leads = 0
    campanhas_com_entrega = 0

    for d in campanhas_data:
        campaign_id = d.get("campaign_id", "")

        # Só processa campanhas ativas com alcance > 0
        alcance = int(d.get("reach", 0))
        if alcance == 0:
            continue
        if campaign_id not in ids_ativas:
            continue

        campanhas_com_entrega += 1
        gasto      = float(d.get("spend", 0))
        impressoes = int(d.get("impressions", 0))
        frequencia = float(d.get("frequency", 0))
        cliques    = int(d.get("clicks", 0))
        ctr        = float(d.get("ctr", 0)) / 100
        cpc        = float(d.get("cpc", 0))
        cpm        = float(d.get("cpm", 0))
        compras    = extrair_action(d, "purchase")
        receita    = extrair_action_value(d, "purchase")
        leads      = extrair_action(d, "lead")
        roas       = receita / gasto if gasto > 0 else 0
        cpa        = gasto / compras if compras > 0 else 0
        cpl        = gasto / leads if leads > 0 else 0

        total_gasto += gasto
        total_alcance += alcance
        total_cliques += cliques
        total_impressoes += impressoes
        total_compras += compras
        total_receita += receita
        total_leads += leads

        salvar("metricas_campanhas", {
            "cliente_id": cliente_id,
            "campaign_id": campaign_id,
            "campaign_name": d.get("campaign_name", ""),
            "data": ontem,
            "status": "ACTIVE",
            "gasto": gasto,
            "impressoes": impressoes,
            "alcance": alcance,
            "frequencia": frequencia,
            "cliques": cliques,
            "conversoes": int(compras),
            "receita": receita,
            "leads": int(leads),
            "ctr": ctr,
            "cpc": cpc,
            "cpm": cpm,
            "cpa": cpa,
            "cpl": cpl,
            "roas": roas,
            "coletado_em": datetime.now().isoformat()
        })

    # Médias ponderadas das campanhas com entrega
    ctr_medio = total_cliques / total_impressoes if total_impressoes > 0 else 0
    cpc_medio = total_gasto / total_cliques if total_cliques > 0 else 0
    cpa_medio = total_gasto / total_compras if total_compras > 0 else 0
    cpl_medio = total_gasto / total_leads if total_leads > 0 else 0
    roas_medio = total_receita / total_gasto if total_gasto > 0 else 0

    # Salva consolidado na tabela de métricas diárias (nível conta)
    salvar("metricas_diarias", {
        "cliente_id": cliente_id,
        "data": ontem,
        "gasto": total_gasto,
        "impressoes": total_impressoes,
        "alcance": total_alcance,
        "frequencia": total_alcance and round(total_impressoes / total_alcance, 3) or 0,
        "cliques": total_cliques,
        "conversoes": int(total_compras),
        "receita": total_receita,
        "leads": int(total_leads),
        "ctr": ctr_medio,
        "cpc": cpc_medio,
        "cpa": cpa_medio,
        "cpl": cpl_medio,
        "roas": roas_medio,
        "coletado_em": datetime.now().isoformat()
    })

    print(f"  📊 {campanhas_com_entrega} camp. com entrega | Gasto: R${total_gasto:.2f} | Alcance: {total_alcance:,} | CTR: {ctr_medio*100:.2f}% | CPC: R${cpc_medio:.2f}")
    return campanhas_data, {"gasto": total_gasto, "alcance": total_alcance}

# === MAIN ===
clientes = buscar_clientes()
if not isinstance(clientes, list):
    print(f"Erro ao buscar clientes: {clientes}")
    exit()

print(f"\n🚀 Coletando {len(clientes)} clientes...\n")
for c in clientes:
    print(f"▶ {c['nome']} ({c['account_id']})")
    if c["plataforma"] in ["meta", "ambos"]:
        campanhas_ativas = coletar_saldo(c["account_id"], c["id"])
        coletar_metricas_campanhas(c["account_id"], c["id"], campanhas_ativas)
    print()

print("✅ Coleta finalizada!")
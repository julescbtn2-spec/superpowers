"""
DCA Bot BTC/USD — Coinbase Advanced Trade
Stratégie d'accumulation Bitcoin pilotée par les métriques on-chain Checkmate.

Prérequis :
    pip install requests
    export COINBASE_API_KEY="..."
    export COINBASE_API_SECRET="..."
"""

import json
import os
import time
import uuid
import hashlib
import hmac
import logging
from datetime import datetime, timezone
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_KEY    = os.environ.get("COINBASE_API_KEY", "")
API_SECRET = os.environ.get("COINBASE_API_SECRET", "")
BASE_URL   = "https://api.coinbase.com"
STATE_FILE = Path(__file__).parent / "state.json"
DCA_AMOUNT = "20.00"   # USD par achat

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("dca_bot")

# ---------------------------------------------------------------------------
# État persistant
# ---------------------------------------------------------------------------

DEFAULT_STATE = {
    "ACTIVE":           False,
    "ACTIVATION_PRICE": None,
    "LAST_DCA_PRICE":   None,
    "LAST_DCA_TS":      None,
    "TOTAL_DCA_BTC":    0.0,
    "DCA_COUNT":        0,
    "CHECKMATE_SCORE":  0.0,
}


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return DEFAULT_STATE.copy()


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ---------------------------------------------------------------------------
# Authentification Coinbase Advanced Trade (ECDSA / JWT-like HMAC)
# ---------------------------------------------------------------------------

def _coinbase_headers(method: str, path: str, body: str = "") -> dict:
    timestamp = str(int(time.time()))
    message   = timestamp + method.upper() + path + body
    signature = hmac.new(
        API_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return {
        "CB-ACCESS-KEY":       API_KEY,
        "CB-ACCESS-SIGN":      signature,
        "CB-ACCESS-TIMESTAMP": timestamp,
        "Content-Type":        "application/json",
    }


def _get(path: str) -> dict:
    headers  = _coinbase_headers("GET", path)
    response = requests.get(BASE_URL + path, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()


def _post(path: str, payload: dict) -> dict:
    body     = json.dumps(payload)
    headers  = _coinbase_headers("POST", path, body)
    response = requests.post(BASE_URL + path, headers=headers, data=body, timeout=10)
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# Vérification des dépendances
# ---------------------------------------------------------------------------

def coinbase_api_ok() -> bool:
    try:
        _get("/api/v3/brokerage/accounts")
        return True
    except Exception:
        log.warning("⚠️ Coinbase API issue - verify connectivity")
        return False


def checkonchain_reachable() -> bool:
    try:
        r = requests.get("https://checkonchain.com", timeout=5)
        return r.status_code < 500
    except Exception:
        log.warning("⚠️ checkonchain.com down - using last metrics")
        return False


def newhedge_reachable() -> bool:
    try:
        r = requests.get("https://newhedge.io", timeout=5)
        return r.status_code < 500
    except Exception:
        log.warning("⚠️ newhedge.io down - using fallback power law")
        return False


# ---------------------------------------------------------------------------
# Données de marché
# ---------------------------------------------------------------------------

def get_btc_price() -> float:
    data = _get("/api/v3/brokerage/products/BTC-USD/ticker")
    return float(data["trades"][0]["price"])


def get_90d_high(price: float) -> float:
    """
    Retourne le plus haut sur 90 jours.
    Remplacer par un appel à l'historique Coinbase ou une source externe.
    Valeur approchée : utilise le prix actuel comme plancher de sécurité.
    """
    # TODO: implémenter via GET /api/v3/brokerage/products/BTC-USD/candles
    return price


def get_fair_value() -> float:
    """
    Fair Value BTC selon le Power Law (newhedge.io).
    Remplacer par un appel API réel ou un calcul local de secours.
    """
    # Formule Power Law approximative (à calibrer)
    days_since_genesis = (datetime.now(timezone.utc) - datetime(2009, 1, 3, tzinfo=timezone.utc)).days
    return 10 ** (5.84 * (days_since_genesis / 365.25) ** 0.402 - 17.01)


# ---------------------------------------------------------------------------
# Métriques on-chain Checkmate
# (à brancher sur l'API checkonchain.com quand disponible)
# ---------------------------------------------------------------------------

def fetch_onchain_metrics() -> dict:
    """
    Retourne un dictionnaire des métriques on-chain.
    Toutes les valeurs sont des approximations par défaut.
    Brancher ici l'API checkonchain.com.
    """
    return {
        "realized_losses_usd":      0,      # USD/jour
        "spot_price":               0,      # USD
        "sth_cost_basis":           0,      # USD
        "seller_exhaustion":        1.0,    # ratio
        "mvrv_z_score":             0.0,
        "exchange_balance_change":  0,      # BTC (négatif = sortie)
        "urpd_node_break":          False,
        "supply_in_loss_pct":       0.0,    # %
        "lth_spending_pct":         0.0,    # %
        "nupl":                     0.0,
        "lth_nupl":                 0.0,
    }


def compute_bottom_score(m: dict) -> float:
    """
    Checkmate Bottom Score (max ~11 pts).
    Désactivation déclenchée si score ≥ 7.
    """
    score = 0.0
    if m["realized_losses_usd"] > 2_000_000_000:
        score += 2.0
    if m["spot_price"] < m["sth_cost_basis"]:
        score += 1.5
    if m["seller_exhaustion"] < 0.1:
        score += 1.5
    if m["mvrv_z_score"] < -2:
        score += 2.0
    if m["exchange_balance_change"] < -100_000:
        score += 2.0
    if m["urpd_node_break"]:
        score += 1.0
    if m["supply_in_loss_pct"] > 50:
        score += 1.0
    return score


def compute_top_score(m: dict) -> float:
    """
    Checkmate Top Score (max 3 pts indicatifs).
    Activation déclenchée si score ≥ 6 — ajouter d'autres indicateurs si besoin.
    """
    score = 0.0
    if m["lth_spending_pct"] > 0.5:
        score += 2.0
    if m["nupl"] > 0.75:
        score += 2.0
    if m["spot_price"] > 2 * m["sth_cost_basis"]:
        score += 2.0
    return score


# ---------------------------------------------------------------------------
# Logique d'activation / désactivation
# ---------------------------------------------------------------------------

def should_activate(price: float, state: dict, metrics: dict) -> bool:
    fair_value  = get_fair_value()
    high_90d    = get_90d_high(price)
    drawdown    = (high_90d - price) / high_90d if high_90d > 0 else 0
    top_score   = compute_top_score(metrics)

    cond1 = (high_90d >= fair_value * 2.3) and (drawdown >= 0.20)
    cond2 = top_score >= 6

    if cond1:
        log.info(f"Activation — Condition 1 : rejet ×2.3 + drawdown {drawdown:.1%}")
    if cond2:
        log.info(f"Activation — Condition 2 : Top Score {top_score}")

    return cond1 or cond2


def should_deactivate(state: dict, bottom_score: float) -> bool:
    if bottom_score >= 7:
        log.info(f"Désactivation — Bottom Score {bottom_score} ≥ 7")
        return True
    if state["DCA_COUNT"] >= 30:
        log.info("Désactivation — DCA_COUNT ≥ 30")
        return True
    return False


# ---------------------------------------------------------------------------
# Exécution d'un achat DCA
# ---------------------------------------------------------------------------

def execute_dca_buy(state: dict, price: float, score: float) -> dict:
    count = state["DCA_COUNT"] + 1
    order_id = f"dca-{count}-{int(time.time())}"

    payload = {
        "client_order_id": order_id,
        "product_id": "BTC-USD",
        "side": "BUY",
        "order_configuration": {
            "market_market_ioc": {
                "quote_size": DCA_AMOUNT,
            }
        },
    }

    result   = _post("/api/v3/brokerage/orders", payload)
    btc_qty  = float(result.get("order", {}).get("filled_size", 0))

    log.info(f"DCA Buy #{count} at ${price:,.2f} | Checkmate Score: {score}")

    state["DCA_COUNT"]       = count
    state["LAST_DCA_PRICE"]  = price
    state["LAST_DCA_TS"]     = datetime.now(timezone.utc).isoformat()
    state["TOTAL_DCA_BTC"]  += btc_qty
    state["CHECKMATE_SCORE"] = score
    return state


# ---------------------------------------------------------------------------
# Logique DCA : décider si un achat est nécessaire
# ---------------------------------------------------------------------------

def should_buy(state: dict, price: float) -> bool:
    last_price = state["LAST_DCA_PRICE"]
    last_ts    = state["LAST_DCA_TS"]

    # Premier achat immédiat
    if last_price is None:
        return True

    # Contrainte : max 1 achat par 24h
    if last_ts:
        last_dt   = datetime.fromisoformat(last_ts)
        now       = datetime.now(timezone.utc)
        hours_ago = (now - last_dt).total_seconds() / 3600
        if hours_ago < 24:
            return False

    # Condition de prix : chute ≥ 7%
    price_drop = (last_price - price) / last_price
    if price_drop >= 0.07 and price <= last_price * 0.93:
        return True

    # Condition de temps : ≥ 21 jours
    if last_ts:
        days_ago = (datetime.now(timezone.utc) - datetime.fromisoformat(last_ts)).days
        if days_ago >= 21:
            return True

    return False


# ---------------------------------------------------------------------------
# Boucle principale
# ---------------------------------------------------------------------------

def run_once() -> None:
    state = load_state()

    # Vérification des dépendances
    checkonchain_reachable()
    newhedge_reachable()
    if not coinbase_api_ok():
        return

    price   = get_btc_price()
    metrics = fetch_onchain_metrics()
    metrics["spot_price"] = price

    bottom_score = compute_bottom_score(metrics)
    state["CHECKMATE_SCORE"] = bottom_score

    # Désactivation
    if state["ACTIVE"] and should_deactivate(state, bottom_score):
        state["ACTIVE"] = False
        save_state(state)
        return

    # Activation
    if not state["ACTIVE"] and should_activate(price, state, metrics):
        state["ACTIVE"]           = True
        state["ACTIVATION_PRICE"] = price
        save_state(state)

    # Achats DCA
    if state["ACTIVE"] and should_buy(state, price):
        state = execute_dca_buy(state, price, bottom_score)

    save_state(state)


if __name__ == "__main__":
    run_once()

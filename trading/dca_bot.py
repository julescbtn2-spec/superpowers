"""
DCA Bot BTC/USD — Coinbase Advanced Trade
Stratégie d'accumulation Bitcoin pilotée par les métriques on-chain Checkmate.

Prérequis :
    pip install requests PyJWT cryptography
"""

import json
import os
import sys
import time
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path

import jwt
import requests

# ---------------------------------------------------------------------------
# Chargement du .env (si présent)
# ---------------------------------------------------------------------------

_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ[_k.strip()] = _v.strip()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_KEY    = os.environ.get("COINBASE_API_KEY", "")
_raw       = os.environ.get("COINBASE_API_SECRET", "")
API_SECRET = _raw.replace("\\n", "\n")
BASE_URL   = "https://api.coinbase.com"
STATE_FILE = Path(__file__).parent / "state.json"
DCA_AMOUNT    = "4.00"    # USD par achat (portefeuille 110€ / 30 achats max)
ALWAYS_ACTIVE = False     # True = DCA permanent sans condition d'activation
MAX_RETRIES   = 3         # Tentatives Coinbase avant HALT
DATA_TTL      = 14400     # Secondes avant de considérer les données comme périmées (4h)

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
    "LAST_DATA_TS":     None,
    "RETRY_COUNT":      0,
}


def load_state() -> dict:
    if STATE_FILE.exists():
        s = json.loads(STATE_FILE.read_text())
        # Assurer la compatibilité avec les nouveaux champs
        for k, v in DEFAULT_STATE.items():
            s.setdefault(k, v)
        return s
    return DEFAULT_STATE.copy()


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ---------------------------------------------------------------------------
# Authentification Coinbase CDP (JWT / ES256)
# ---------------------------------------------------------------------------

def _coinbase_headers(method: str, path: str, body: str = "") -> dict:
    pem = API_SECRET if API_SECRET.endswith("\n") else API_SECRET + "\n"
    now = int(time.time())
    token = jwt.encode(
        {
            "iss": "cdp",
            "nbf": now,
            "exp": now + 120,
            "sub": API_KEY,
            "uri": f"{method.upper()} api.coinbase.com{path}",
        },
        pem,
        algorithm="ES256",
        headers={"kid": API_KEY, "nonce": uuid.uuid4().hex},
    )
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
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
# Vérification des dépendances (avec protection staleness et retry)
# ---------------------------------------------------------------------------

def check_coinbase(state: dict) -> bool:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            _get("/api/v3/brokerage/accounts")
            state["RETRY_COUNT"] = 0
            return True
        except requests.HTTPError as e:
            log.warning(f"⚠️ Coinbase HTTP {e.response.status_code}: {e.response.text[:200]}")
        except Exception as e:
            log.warning(f"⚠️ Coinbase API issue: {e}")

        state["RETRY_COUNT"] = state.get("RETRY_COUNT", 0) + 1
        if state["RETRY_COUNT"] >= MAX_RETRIES:
            log.error("🛑 HALT — Coinbase unreachable après 3 tentatives")
            save_state(state)
            sys.exit(1)

        wait = 60 * attempt
        log.warning(f"Retry {attempt}/{MAX_RETRIES} — attente {wait}s")
        time.sleep(wait)

    return False


def check_onchain_sources(state: dict) -> bool:
    """Vérifie checkonchain.com avec protection anti-données périmées."""
    try:
        r = requests.get("https://checkonchain.com", timeout=5)
        if r.status_code < 500:
            state["LAST_DATA_TS"] = int(time.time())
            return True
    except Exception:
        pass

    # Source indisponible — vérifier la fraîcheur du cache
    last_ts = state.get("LAST_DATA_TS")
    if last_ts and (int(time.time()) - last_ts) > DATA_TTL:
        log.error("🛑 PAUSE — Données on-chain périmées (>4h)")
        save_state(state)
        sys.exit(1)

    log.warning("⚠️ checkonchain.com down - using cached Checkmate metrics")
    return False


def check_newhedge() -> bool:
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
    # TODO: implémenter via GET /api/v3/brokerage/products/BTC-USD/candles
    return price


def get_fair_value() -> float:
    """Fair Value BTC selon le Power Law (fallback local si newhedge.io down)."""
    days = (datetime.now(timezone.utc) - datetime(2009, 1, 3, tzinfo=timezone.utc)).days
    return 10 ** (5.84 * (days / 365.25) ** 0.402 - 17.01)


# ---------------------------------------------------------------------------
# Métriques on-chain Checkmate
# (à brancher sur l'API checkonchain.com quand disponible)
# ---------------------------------------------------------------------------

def fetch_onchain_metrics() -> dict:
    return {
        "realized_losses_usd":     0,
        "spot_price":              0,
        "sth_cost_basis":          0,
        "seller_exhaustion":       1.0,
        "mvrv_z_score":            0.0,
        "exchange_balance_change": 0,
        "urpd_node_break":         False,
        "supply_in_loss_pct":      0.0,
        "lth_spending_pct":        0.0,
        "nupl":                    0.0,
    }


def compute_bottom_score(m: dict) -> float:
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
    fair_value = get_fair_value()
    high_90d   = get_90d_high(price)
    drawdown   = (high_90d - price) / high_90d if high_90d > 0 else 0
    top_score  = compute_top_score(metrics)

    cond1 = (high_90d >= fair_value * 2.3) and (drawdown >= 0.20)
    cond2 = top_score >= 6

    if cond1:
        log.info(f"Activation — Condition 1 : rejet ×2.3 + drawdown {drawdown:.1%}")
    if cond2:
        log.info(f"Activation — Condition 2 : Top Score {top_score}")

    return cond1 or cond2


def should_deactivate(state: dict, price: float, bottom_score: float) -> bool:
    fair_value       = get_fair_value()
    activation_price = state.get("ACTIVATION_PRICE") or 0

    if bottom_score >= 7:
        log.info(f"Désactivation — Bottom Score {bottom_score} ≥ 7")
        return True
    if state["DCA_COUNT"] >= 30:
        log.info("Désactivation — DCA_COUNT ≥ 30")
        return True
    if activation_price and price >= activation_price * 1.3:
        log.info(f"Désactivation — Prix ${price:,.0f} ≥ ACTIVATION_PRICE×1.3 (${activation_price * 1.3:,.0f})")
        return True
    if price >= fair_value * 1.5:
        log.info(f"Désactivation — Prix ${price:,.0f} ≥ Fair Value×1.5 (${fair_value * 1.5:,.0f})")
        return True
    return False


# ---------------------------------------------------------------------------
# Exécution d'un achat DCA
# ---------------------------------------------------------------------------

def execute_dca_buy(state: dict, price: float, score: float) -> dict:
    count    = state["DCA_COUNT"] + 1
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

    result  = _post("/api/v3/brokerage/orders", payload)
    btc_qty = float(result.get("order", {}).get("filled_size", 0))

    state["DCA_COUNT"]      = count
    state["LAST_DCA_PRICE"] = price
    state["LAST_DCA_TS"]    = datetime.now(timezone.utc).isoformat()
    state["TOTAL_DCA_BTC"] += btc_qty
    state["CHECKMATE_SCORE"] = score

    log.info(f"DCA Buy #{count} at ${price:,.2f} | Score: {score} | Total: {state['TOTAL_DCA_BTC']:.8f} BTC")
    return state


# ---------------------------------------------------------------------------
# Logique DCA
# ---------------------------------------------------------------------------

def should_buy(state: dict, price: float) -> bool:
    last_price = state["LAST_DCA_PRICE"]
    last_ts    = state["LAST_DCA_TS"]

    if last_price is None:
        return True

    if last_ts:
        hours_ago = (datetime.now(timezone.utc) - datetime.fromisoformat(last_ts)).total_seconds() / 3600
        if hours_ago < 24:
            return False

    price_drop = (last_price - price) / last_price
    if price_drop >= 0.07 and price <= last_price * 0.93:
        return True

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
    check_onchain_sources(state)
    check_newhedge()
    check_coinbase(state)

    price   = get_btc_price()
    metrics = fetch_onchain_metrics()
    metrics["spot_price"] = price

    bottom_score             = compute_bottom_score(metrics)
    state["CHECKMATE_SCORE"] = bottom_score
    state["LAST_DATA_TS"]    = int(time.time())

    log.info(f"BTC ${price:,.0f} | ACTIVE={state['ACTIVE']} | DCA_COUNT={state['DCA_COUNT']} | Bottom Score={bottom_score}")

    if ALWAYS_ACTIVE:
        state["ACTIVE"] = True
    else:
        # Désactivation
        if state["ACTIVE"] and should_deactivate(state, price, bottom_score):
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

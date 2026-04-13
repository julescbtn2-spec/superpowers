"""
Exemple de simulation du DCA Bot BTC/USD — sans clés API réelles.

Exécution :
    python3 trading/example.py

Ce script rejoue un scénario complet :
  1. Détection d'un top de marché → activation
  2. Série d'achats DCA ($20 chacun)
  3. Détection d'un bottom on-chain → désactivation
"""

from datetime import datetime, timezone, timedelta
import json

# ---------------------------------------------------------------------------
# État initial
# ---------------------------------------------------------------------------

state = {
    "ACTIVE":           False,
    "ACTIVATION_PRICE": None,
    "LAST_DCA_PRICE":   None,
    "LAST_DCA_TS":      None,
    "TOTAL_DCA_BTC":    0.0,
    "DCA_COUNT":        0,
    "CHECKMATE_SCORE":  0.0,
}

def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    print(f"[{ts}] {msg}")

def print_state(state):
    print()
    print("  ┌─────────────────────────────────────────┐")
    print(f"  │ ACTIVE          : {str(state['ACTIVE']):<24}│")
    print(f"  │ ACTIVATION_PRICE: ${state['ACTIVATION_PRICE'] or 'null':<23}│")
    print(f"  │ LAST_DCA_PRICE  : ${state['LAST_DCA_PRICE'] or 'null':<23}│")
    print(f"  │ DCA_COUNT       : {state['DCA_COUNT']:<24}│")
    print(f"  │ TOTAL_DCA_BTC   : {state['TOTAL_DCA_BTC']:.8f} BTC         │")
    print(f"  │ CHECKMATE_SCORE : {state['CHECKMATE_SCORE']:<24}│")
    print("  └─────────────────────────────────────────┘")
    print()

# ---------------------------------------------------------------------------
# Scoring Checkmate (même logique que dca_bot.py)
# ---------------------------------------------------------------------------

def compute_bottom_score(m):
    score = 0.0
    if m["realized_losses_usd"] > 2_000_000_000:
        score += 2.0
        print(f"    [+2.0] Realized Losses ${m['realized_losses_usd']/1e9:.1f}B > $2B/jour")
    if m["spot_price"] < m["sth_cost_basis"]:
        score += 1.5
        print(f"    [+1.5] Spot ${m['spot_price']:,} < STH Cost ${m['sth_cost_basis']:,}")
    if m["seller_exhaustion"] < 0.1:
        score += 1.5
        print(f"    [+1.5] Seller Exhaustion {m['seller_exhaustion']} < 0.1")
    if m["mvrv_z_score"] < -2:
        score += 2.0
        print(f"    [+2.0] MVRV Z-Score {m['mvrv_z_score']} < -2")
    if m["exchange_balance_change"] < -100_000:
        score += 2.0
        print(f"    [+2.0] Exchange Balance -{abs(m['exchange_balance_change']):,} BTC")
    if m["urpd_node_break"]:
        score += 1.0
        print(f"    [+1.0] URPD Node Break détecté")
    if m["supply_in_loss_pct"] > 50:
        score += 1.0
        print(f"    [+1.0] Supply in Loss {m['supply_in_loss_pct']}% > 50%")
    return score

def compute_top_score(m):
    score = 0.0
    if m["lth_spending_pct"] > 0.5:
        score += 2.0
        print(f"    [+2.0] LTH Spending {m['lth_spending_pct']}% > 0.5%")
    if m["nupl"] > 0.75:
        score += 2.0
        print(f"    [+2.0] NUPL {m['nupl']} > 0.75")
    if m["spot_price"] > 2 * m["sth_cost_basis"]:
        score += 2.0
        print(f"    [+2.0] Spot ${m['spot_price']:,} > 2× STH ${m['sth_cost_basis']:,}")
    return score

# ---------------------------------------------------------------------------
# Simulation d'un achat DCA (pas de vraie API)
# ---------------------------------------------------------------------------

def simulate_buy(state, price, score):
    count   = state["DCA_COUNT"] + 1
    btc_qty = 20.0 / price  # $20 / prix actuel

    log(f"DCA Buy #{count} at ${price:,} | Checkmate Score: {score}")
    log(f"  → {btc_qty:.8f} BTC achetés pour $20.00")

    state["DCA_COUNT"]       = count
    state["LAST_DCA_PRICE"]  = price
    state["LAST_DCA_TS"]     = datetime.now(timezone.utc).isoformat()
    state["TOTAL_DCA_BTC"]  += btc_qty
    state["CHECKMATE_SCORE"] = score
    return state

def can_buy(state, price, now):
    last_price = state["LAST_DCA_PRICE"]
    last_ts    = state["LAST_DCA_TS"]

    if last_price is None:
        return True, "Premier achat immédiat"

    if last_ts:
        last_dt   = datetime.fromisoformat(last_ts)
        hours_ago = (now - last_dt).total_seconds() / 3600
        if hours_ago < 24:
            return False, f"Trop récent ({hours_ago:.1f}h < 24h)"

    drop = (last_price - price) / last_price
    if drop >= 0.07 and price <= last_price * 0.93:
        return True, f"Baisse de {drop:.1%} ≥ 7%"

    if last_ts:
        days = (now - datetime.fromisoformat(last_ts)).days
        if days >= 21:
            return True, f"{days} jours écoulés ≥ 21j"

    return False, f"Conditions non remplies (drop={drop:.1%})"

# ---------------------------------------------------------------------------
# SCÉNARIO : cycle de marché BTC 2025
# ---------------------------------------------------------------------------

print("=" * 55)
print(" SIMULATION DCA BOT — BTC/USD (Coinbase)")
print("=" * 55)

# ── Étape 1 : marché au sommet, pas encore de top signal ──────────────────
print("\n── Étape 1 : BTC à $95 000, marché haussier ──")
price = 95_000
metrics_top = {
    "spot_price": price, "sth_cost_basis": 42_000,
    "lth_spending_pct": 0.2, "nupl": 0.60,
    "realized_losses_usd": 100_000_000, "seller_exhaustion": 0.5,
    "mvrv_z_score": 1.2, "exchange_balance_change": -20_000,
    "urpd_node_break": False, "supply_in_loss_pct": 5.0,
}
top_score = compute_top_score(metrics_top)
log(f"Top Score = {top_score} (seuil : 6) → bot INACTIF")
print_state(state)

# ── Étape 2 : distribution LTH, NUPL extrême → activation ─────────────────
print("\n── Étape 2 : signaux de top Checkmate ──")
price = 108_000
metrics_top2 = {
    "spot_price": price, "sth_cost_basis": 42_000,
    "lth_spending_pct": 0.8,   # > 0.5% ✓
    "nupl": 0.82,               # > 0.75 ✓
    "realized_losses_usd": 200_000_000,
    "seller_exhaustion": 0.4,
    "mvrv_z_score": 1.8,
    "exchange_balance_change": -5_000,
    "urpd_node_break": False, "supply_in_loss_pct": 3.0,
}
top_score2 = compute_top_score(metrics_top2)
log(f"Top Score = {top_score2} ≥ 6 → ACTIVATION du bot !")
state["ACTIVE"]           = True
state["ACTIVATION_PRICE"] = price
print_state(state)

# ── Étape 3 : correction, premier achat immédiat ───────────────────────────
print("\n── Étape 3 : BTC chute à $78 000, premier achat ──")
price = 78_000
now   = datetime.now(timezone.utc)
ok, reason = can_buy(state, price, now)
log(f"Condition d'achat : {reason}")
state = simulate_buy(state, price, 0.0)
print_state(state)

# ── Étape 4 : baisse de 8% → deuxième achat ───────────────────────────────
print("\n── Étape 4 : BTC à $71 000 (−9%), 25h plus tard ──")
price = 71_000
now   = datetime.now(timezone.utc) + timedelta(hours=25)
state["LAST_DCA_TS"] = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
ok, reason = can_buy(state, price, now)
log(f"Condition d'achat : {reason} → {'✓' if ok else '✗'}")
if ok:
    state = simulate_buy(state, price, 1.5)
print_state(state)

# ── Étape 5 : baisse modérée (−3%) → pas d'achat ──────────────────────────
print("\n── Étape 5 : BTC à $69 000 (−3%), 2h plus tard ──")
price = 69_000
now   = datetime.now(timezone.utc) + timedelta(hours=2)
state["LAST_DCA_TS"] = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
ok, reason = can_buy(state, price, now)
log(f"Condition d'achat : {reason} → {'✓' if ok else '✗'}")
print_state(state)

# ── Étape 6 : bottom on-chain confirmé → désactivation ────────────────────
print("\n── Étape 6 : capitulation — Bottom Score Checkmate ──")
price = 38_000
metrics_bottom = {
    "spot_price": price, "sth_cost_basis": 45_000,   # spot < STH ✓
    "realized_losses_usd": 3_500_000_000,             # > $2B ✓
    "seller_exhaustion": 0.05,                        # < 0.1 ✓
    "mvrv_z_score": -2.4,                             # < -2 ✓
    "exchange_balance_change": -150_000,              # > 100k ✓
    "urpd_node_break": True,                          # ✓
    "supply_in_loss_pct": 55.0,                       # > 50% ✓
    "lth_spending_pct": 0.1, "nupl": 0.1,
}
bottom_score = compute_bottom_score(metrics_bottom)
log(f"Bottom Score = {bottom_score} ≥ 7 → DÉSACTIVATION !")
state["ACTIVE"]          = False
state["CHECKMATE_SCORE"] = bottom_score
print_state(state)

# ── Résumé final ───────────────────────────────────────────────────────────
print("=" * 55)
print(" RÉSUMÉ DU CYCLE")
print("=" * 55)
total_usd = state["DCA_COUNT"] * 20
avg_price = (total_usd / state["TOTAL_DCA_BTC"]) if state["TOTAL_DCA_BTC"] > 0 else 0
print(f"  Achats effectués  : {state['DCA_COUNT']}")
print(f"  USD investis      : ${total_usd:.2f}")
print(f"  BTC accumulés     : {state['TOTAL_DCA_BTC']:.8f} BTC")
print(f"  Prix moyen d'achat: ${avg_price:,.2f}")
print(f"  Prix de sortie    : ${price:,}  (bottom confirmé)")
print(f"  Variation / entrée: {((price - state['ACTIVATION_PRICE']) / state['ACTIVATION_PRICE']):.1%}")
print("=" * 55)

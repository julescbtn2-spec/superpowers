# DCA Bot BTC/USD — Note de Trading Coinbase

> Stratégie d'accumulation Bitcoin par DCA conditionnel, pilotée par les métriques on-chain Checkmate.

---

## État courant

| Variable         | Valeur       |
|-----------------|--------------|
| ACTIVE          | `false`      |
| ACTIVATION_PRICE| `null`       |
| LAST_DCA_PRICE  | `null`       |
| LAST_DCA_TS     | `null`       |
| TOTAL_DCA_BTC   | `0`          |
| DCA_COUNT       | `0`          |
| CHECKMATE_SCORE | `0`          |

---

## Sources de données & dépendances

| Source              | Donnée                            | Fallback                              |
|--------------------|-----------------------------------|---------------------------------------|
| Coinbase API        | Prix BTC/USD spot                 | ⚠️ Vérifier la connectivité           |
| checkonchain.com    | Métriques on-chain Checkmate      | ⚠️ Utiliser les dernières métriques   |
| newhedge.io         | Fair Value (Power Law)            | ⚠️ Utiliser le Power Law de secours   |

```
if not checkonchain_reachable(): Log "⚠️ checkonchain.com down - using last metrics"
if not newhedge_reachable():     Log "⚠️ newhedge.io down - using fallback power law"
if not coinbase_api_ok():        Log "⚠️ Coinbase API issue - verify connectivity"
```

---

## Règles d'activation (`ACTIVE = true`)

Le bot s'active si **l'une** des deux conditions est remplie :

**Condition 1 — Rejet de prix extrême :**
- Prix ayant atteint ≥ `Fair Value × 2.3`
- ET drawdown ≥ 20% depuis le plus haut sur 90 jours

**Condition 2 — Checkmate Top Score ≥ 6 :**
| Indicateur                    | Seuil           |
|-------------------------------|-----------------|
| LTH Spending (distribution)   | > 0.5%          |
| NUPL                          | > 0.75          |
| Spot Price                    | > 2 × STH Cost  |

---

## Règles de désactivation (`ACTIVE = false`)

La stratégie s'arrête si **l'une** des deux conditions est remplie :

- **Checkmate Bottom Score ≥ 7** (voir tableau de scoring ci-dessous)
- **OU** `DCA_COUNT ≥ 30`

---

## Règles DCA (pendant `ACTIVE = true`)

### Premier achat
- Achat **immédiat** de `$20` en BTC dès l'activation

### Achats suivants
Déclencher un achat de `$20` en BTC si **l'une** des conditions est vraie :

| Condition              | Valeur                                    |
|------------------------|-------------------------------------------|
| Baisse de prix         | Prix actuel ≤ `LAST_DCA_PRICE × 0.93`    |
| Délai écoulé           | ≥ 21 jours depuis `LAST_DCA_TS`           |

### Contraintes
- Chute **minimum de 7%** entre deux achats consécutifs
- **Maximum 1 achat** par période de 24 heures

### Log de chaque achat
```
DCA Buy #[COUNT] at $[PRICE] | Checkmate Score: [SCORE]
```

---

## Checkmate Bottom Score

Score composite sur ~12 points. Désactivation si total **≥ 7**.

| Indicateur                        | Seuil de déclenchement        | Points |
|-----------------------------------|-------------------------------|--------|
| Realized Losses                   | > $2B / jour                  | 2.0    |
| Spot Price vs STH Cost Basis      | Spot < STH Cost Basis         | 1.5    |
| Seller Exhaustion                 | < 0.1                         | 1.5    |
| MVRV Z-Score                      | < -2                          | 2.0    |
| Exchange Balance Change           | Déclin > 100 000 BTC          | 2.0    |
| URPD Node Break                   | Cassure de nœud URPD          | 1.0    |
| Supply in Loss                    | > 50%                         | 1.0    |
| **Total maximum**                 |                               | **11** |

---

## Configuration API Coinbase

### Prérequis
1. Compte Coinbase vérifié (KYC validé)
2. Dépôt USD disponible sur le compte

### Créer une clé API
1. Connexion sur **coinbase.com**
2. **Paramètres → API → Nouvelle clé API**
3. Permissions requises : `trade` + `view`
4. Conserver la **clé** (`API_KEY`) et le **secret** (`API_SECRET`) — affichés une seule fois

### Variables d'environnement
```bash
export COINBASE_API_KEY="organizations/xxx/apiKeys/yyy"
export COINBASE_API_SECRET="-----BEGIN EC PRIVATE KEY-----\n...\n-----END EC PRIVATE KEY-----"
```

### Endpoints utilisés

| Action                  | Méthode | Endpoint                                          |
|------------------------|---------|--------------------------------------------------|
| Prix spot BTC/USD       | GET     | `/api/v3/brokerage/products/BTC-USD/ticker`      |
| Passer un ordre marché  | POST    | `/api/v3/brokerage/orders`                       |
| Vérifier connectivité   | GET     | `/api/v3/brokerage/accounts`                     |

### Payload d'un ordre DCA ($20)
```json
{
  "client_order_id": "dca-{COUNT}-{TIMESTAMP}",
  "product_id": "BTC-USD",
  "side": "BUY",
  "order_configuration": {
    "market_market_ioc": {
      "quote_size": "20.00"
    }
  }
}
```

### Fichier de configuration du bot
Voir `trading/dca_bot.py` pour l'implémentation complète.

---

## Historique des transactions

| # | Date | Prix (USD) | Montant ($) | BTC acheté | Checkmate Score |
|---|------|-----------|-------------|------------|-----------------|
| — | —    | —         | —           | —          | —               |

---

## Notes

- Toutes les décisions sont basées sur des données on-chain objectives, sans signal discrétionnaire.
- Le cycle complet se termine après 30 achats (`DCA_COUNT = 30`) ou lors d'un bottom on-chain confirmé.
- Réinitialiser l'état après désactivation avant de relancer un nouveau cycle.

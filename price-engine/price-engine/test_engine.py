# HASINEH MARKET
# HASINEH PRICE ENGINE V1
# TEST ENGINE
# Bandar Hasineh
# Hassan Divanizadeh

from datetime import datetime

print("=" * 60)
print("HASINEH MARKET - PRICE ENGINE V1")
print("TEST ENGINE")
print("=" * 60)

# -----------------------------
# TEST MARKET INPUT
# -----------------------------

market_data = {
    "gold_18k": 23500000,
    "gold_24k": 31333333,
    "coin_emami": 185000000,
    "coin_half": 99000000,
    "coin_quarter": 56000000,
    "silver": 420000,
    "usd": 105000,
    "eur": 123000,
    "aed": 29000,
    "usdt": 105500
}

# -----------------------------
# PRICE ENGINE
# -----------------------------

def calculate_market_status(price, previous_price):
    if price > previous_price:
        return "UP"
    elif price < previous_price:
        return "DOWN"
    else:
        return "STABLE"


def calculate_change(price, previous_price):
    if previous_price == 0:
        return 0

    return ((price - previous_price) / previous_price) * 100


# -----------------------------
# PREVIOUS TEST PRICES
# -----------------------------

previous_data = {
    "gold_18k": 23400000,
    "gold_24k": 31200000,
    "coin_emami": 184000000,
    "coin_half": 98500000,
    "coin_quarter": 55500000,
    "silver": 415000,
    "usd": 104500,
    "eur": 122000,
    "aed": 28800,
    "usdt": 105000
}

# -----------------------------
# ENGINE OUTPUT
# -----------------------------

print("\nPRICE ENGINE RESULT")
print("-" * 60)

for name, price in market_data.items():

    previous_price = previous_data.get(name, price)

    status = calculate_market_status(
        price,
        previous_price
    )

    change = calculate_change(
        price,
        previous_price
    )

    print(
        f"{name:15} "
        f"{price:>12,} "
        f"{status:>8} "
        f"{change:+.2f}%"
    )

# -----------------------------
# ENGINE STATUS
# -----------------------------

print("\n" + "=" * 60)

required_items = [
    "gold_18k",
    "gold_24k",
    "coin_emami",
    "coin_half",
    "coin_quarter",
    "silver",
    "usd",
    "eur",
    "aed",
    "usdt"
]

engine_ready = all(
    item in market_data
    for item in required_items
)

if engine_ready:
    print("ENGINE STATUS : READY")
    print("DATA TEST     : PASSED")
else:
    print("ENGINE STATUS : ERROR")
    print("DATA TEST     : FAILED")

# -----------------------------
# TIME
# -----------------------------

now = datetime.now()

print(
    "TEST TIME     :",
    now.strftime("%Y-%m-%d %H:%M:%S")
)

print("=" * 60)
print("HASINEH MARKET PRICE ENGINE V1")
print("TEST COMPLETE")
print("=" * 60)

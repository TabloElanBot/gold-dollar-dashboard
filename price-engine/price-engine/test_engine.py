# HASINEH MARKET
# HASINEH PRICE ENGINE V1
# REAL JSON TEST ENGINE
# Bandar Hasineh
# Hassan Divanizadeh

import json
import os
from datetime import datetime


print("=" * 60)
print("HASINEH MARKET - PRICE ENGINE V1")
print("REAL JSON TEST ENGINE")
print("=" * 60)


# --------------------------------
# LOAD PRICES JSON
# --------------------------------

json_file = "price-engine/prices.json"


if not os.path.exists(json_file):

    print("ERROR: prices.json NOT FOUND")
    raise SystemExit(1)


with open(
    json_file,
    "r",
    encoding="utf-8"
) as file:

    data = json.load(file)



# --------------------------------
# BASIC CHECK
# --------------------------------

print("\nJSON CHECK")
print("-" * 60)


required_main = [
    "engine",
    "status",
    "source",
    "prices"
]


for item in required_main:

    if item not in data:

        print(
            "MISSING:",
            item
        )

        raise SystemExit(1)


print("JSON STRUCTURE : OK")



# --------------------------------
# PRICE CHECK
# --------------------------------

prices = data["prices"]


required_prices = [

    "gold_18k",
    "gold_24k",
    "gold_melted",
    "coin_emami",
    "coin_half",
    "coin_quarter",
    "coin_bahar",
    "usd",
    "eur",
    "aed",
    "usdt"

]


print("\nPRICE CHECK")
print("-" * 60)


for item in required_prices:

    if item not in prices:

        print(
            "MISSING PRICE:",
            item
        )

        raise SystemExit(1)


    value = prices[item]


    if not isinstance(value, (int, float)):

        print(
            "INVALID PRICE:",
            item
        )

        raise SystemExit(1)


    if value <= 0:

        print(
            "ZERO PRICE:",
            item
        )

        raise SystemExit(1)


    print(
        f"{item:15} {value:>15,} OK"
    )



# --------------------------------
# ENGINE STATUS
# --------------------------------

print("\nENGINE STATUS")
print("-" * 60)


print(
    "ENGINE:",
    data["engine"]
)

print(
    "STATUS:",
    data["status"]
)

print(
    "SOURCE:",
    data["source"]
)


print(
    "DATA TEST : PASSED"
)



# --------------------------------
# TIME
# --------------------------------

now = datetime.now()


print("\nTEST TIME:")
print(
    now.strftime(
        "%Y-%m-%d %H:%M:%S"
    )
)


print("=" * 60)
print("HASINEH PRICE ENGINE V1")
print("TEST COMPLETE")
print("=" * 60)

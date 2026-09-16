import json
import os
import traceback
from datetime import datetime

print("=" * 60)
print("HASINEH MARKET - PRICE ENGINE V1")
print("REAL JSON TEST ENGINE")
print("=" * 60)

try:
    json_file = "price-engine/prices.json"

    print("\nFILE CHECK")
    print("-" * 60)
    print("FILE:", json_file)

    if not os.path.exists(json_file):
        print("ERROR: prices.json NOT FOUND")
        raise SystemExit(1)

    print("prices.json : FOUND")

    with open(json_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    print("JSON LOAD : OK")

    print("\nJSON CHECK")
    print("-" * 60)

    if not isinstance(data, dict):
        print("ERROR: JSON ROOT IS NOT AN OBJECT")
        raise SystemExit(1)

    required_main = [
        "engine",
        "status",
        "source",
        "prices"
    ]

    for item in required_main:
        if item not in data:
            print("MISSING MAIN FIELD:", item)
            raise SystemExit(1)

    print("JSON STRUCTURE : OK")

    prices = data["prices"]

    if not isinstance(prices, dict):
        print("ERROR: prices IS NOT AN OBJECT")
        raise SystemExit(1)

    print("PRICES OBJECT : OK")

    required_prices = [
        "gold_18k",
        "gold_24k",
        "gold_melted",
        "coin_emami",
        "coin_half",
        "coin_quarter",
        "usd",
        "eur",
        "aed",
        "usdt"
    ]

    print("\nPRICE CHECK")
    print("-" * 60)

    failed = False

    for item in required_prices:
        if item not in prices:
            print("MISSING PRICE:", item)
            failed = True
            continue

        value = prices[item]

        if isinstance(value, bool):
            print("INVALID PRICE:", item)
            failed = True
            continue

        if not isinstance(value, (int, float)):
            print("INVALID PRICE:", item, "VALUE:", value)
            failed = True
            continue

        if value <= 0:
            print("ZERO/NEGATIVE PRICE:", item, "VALUE:", value)
            failed = True
            continue

        print(f"{item:15} {value:>15,} OK")

    if failed:
        print("\nPRICE TEST : FAILED")
        raise SystemExit(1)

    print("\nPRICE TEST : PASSED")

    optional_prices = [
        "coin_bahar",
        "silver_999",
        "silver_925",
        "gbp",
        "try",
        "cny",
        "gold_21k_mesghal"
    ]

    print("\nOPTIONAL PRICE CHECK")
    print("-" * 60)

    for item in optional_prices:
        if item not in prices:
            print(f"{item:20} NOT PRESENT (OPTIONAL)")
            continue

        value = prices[item]

        if isinstance(value, bool):
            print(f"{item:20} INVALID")
            continue

        if not isinstance(value, (int, float)):
            print(f"{item:20} INVALID")
            continue

        if value <= 0:
            print(f"{item:20} INVALID VALUE")
            continue

        print(f"{item:20} {value:>15,} OK")

    print("\nENGINE STATUS")
    print("-" * 60)
    print("ENGINE:", data["engine"])
    print("STATUS:", data["status"])
    print("SOURCE:", data["source"])

    print("\nDATA TEST : PASSED")

    now = datetime.now()

    print("\nTEST TIME:")
    print(now.strftime("%Y-%m-%d %H:%M:%S"))

    print("=" * 60)
    print("HASINEH PRICE ENGINE V1")
    print("TEST COMPLETE - SUCCESS")
    print("=" * 60)

except SystemExit:
    raise

except Exception:
    print("\n" + "=" * 60)
    print("UNEXPECTED ERROR")
    print("=" * 60)
    traceback.print_exc()
    raise SystemExit(1)

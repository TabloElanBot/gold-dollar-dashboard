# ================================================================
# HASINEH PRICE ENGINE
# TEST ENGINE V2
# ================================================================

import json
import os
import sys
from datetime import datetime, timezone


# ================================================================
# SETTINGS
# ================================================================

PRICE_FILE = "price-engine/prices.json"

REQUIRED_PRICES = [
    "gold_18k",
    "gold_24k",
    "gold_melted",
    "coin_emami",
    "coin_half",
    "coin_quarter",
    "usd",
    "eur",
    "aed",
    "usdt",
]


OPTIONAL_PRICES = [
    "gbp",
    "try",
    "cny",
    "silver_999",
    "silver_925",
    "gold_21k_mesghal",
]


# ================================================================
# TEST HELPERS
# ================================================================

def fail(message):
    print("")
    print("[FAIL]", message)
    print("")
    sys.exit(1)


def success(message):
    print("[OK]", message)


# ================================================================
# START
# ================================================================

print("")
print("=" * 64)
print("HASINEH PRICE ENGINE TEST V2")
print("=" * 64)
print("")


# ================================================================
# CHECK FILE
# ================================================================

if not os.path.exists(PRICE_FILE):
    fail(
        "prices.json was not found: "
        + PRICE_FILE
    )

success("prices.json exists")


# ================================================================
# LOAD JSON
# ================================================================

try:

    with open(
        PRICE_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

except Exception as error:

    fail(
        "Could not read prices.json: "
        + str(error)
    )


# ================================================================
# ROOT OBJECT
# ================================================================

if not isinstance(data, dict):
    fail("JSON root is not an object")

success("JSON root is valid")


# ================================================================
# REQUIRED ROOT FIELDS
# ================================================================

required_root_fields = [
    "engine",
    "status",
    "source",
    "prices",
]


for field in required_root_fields:

    if field not in data:
        fail(
            "Missing root field: "
            + field
        )

success("Required root fields exist")


# ================================================================
# PRICES OBJECT
# ================================================================

prices = data["prices"]

if not isinstance(prices, dict):
    fail("prices is not an object")

success("prices object is valid")


# ================================================================
# CHECK PRICE ITEMS
#
# Supports both:
#
# OLD FORMAT:
# "gold_18k": 23000000
#
# NEW FORMAT:
# "gold_18k": {
#     "price": 23000000,
#     "status": "live",
#     ...
# }
# ================================================================

live_count = 0
calculated_count = 0
not_found_count = 0


for key in REQUIRED_PRICES:

    if key not in prices:
        fail(
            "Missing required price: "
            + key
        )

    item = prices[key]


    # ------------------------------------------------------------
    # NEW FORMAT
    # ------------------------------------------------------------

    if isinstance(item, dict):

        if "price" not in item:
            fail(
                "Missing price field for: "
                + key
            )

        value = item["price"]
        status = item.get(
            "status",
            "unknown"
        )


    # ------------------------------------------------------------
    # OLD FORMAT
    # ------------------------------------------------------------

    elif isinstance(item, (int, float)):

        value = item
        status = "live"


    else:

        fail(
            "Invalid price format for: "
            + key
        )


    # ------------------------------------------------------------
    # VALUE CHECK
    # ------------------------------------------------------------

    if value is not None:

        if not isinstance(
            value,
            (int, float)
        ):
            fail(
                "Price is not numeric for: "
                + key
            )

        if value < 0:
            fail(
                "Negative price detected for: "
                + key
            )


    # ------------------------------------------------------------
    # STATUS COUNT
    # ------------------------------------------------------------

    if status == "live":
        live_count += 1

    elif status == "calculated":
        calculated_count += 1

    elif status == "not_found":
        not_found_count += 1


    success(
        key
        + " = "
        + str(value)
        + " ["
        + str(status)
        + "]"
    )


# ================================================================
# OPTIONAL PRICES
# ================================================================

for key in OPTIONAL_PRICES:

    if key not in prices:
        print(
            "[INFO] Optional price not present:",
            key
        )
        continue

    item = prices[key]

    if isinstance(item, dict):

        value = item.get("price")
        status = item.get(
            "status",
            "unknown"
        )

    elif isinstance(item, (int, float)):

        value = item
        status = "live"

    else:

        fail(
            "Invalid optional price format for: "
            + key
        )

    if value is not None:

        if not isinstance(
            value,
            (int, float)
        ):
            fail(
                "Optional price is not numeric for: "
                + key
            )

    print(
        "[INFO]",
        key,
        "=",
        value,
        "[",
        status,
        "]"
    )


# ================================================================
# FAKE PRICE CHECK
# ================================================================

if data.get(
    "fake_prices_allowed",
    False
) is True:

    fail(
        "fake_prices_allowed is TRUE"
    )

success("Fake prices are disabled")


# ================================================================
# ENGINE STATUS
# ================================================================

engine_status = data.get(
    "status",
    "unknown"
)

print("")
print(
    "[ENGINE STATUS]",
    engine_status
)

print(
    "[LIVE ITEMS]",
    live_count
)

print(
    "[CALCULATED ITEMS]",
    calculated_count
)

print(
    "[NOT FOUND ITEMS]",
    not_found_count
)


# ================================================================
# FINAL VALIDATION
# ================================================================

if live_count == 0:

    fail(
        "No live prices were collected"
    )


# ================================================================
# TEST TIME
# ================================================================

test_time = datetime.now(
    timezone.utc
).isoformat()


print("")
print(
    "[TEST TIME UTC]",
    test_time
)

print("")
print("=" * 64)
print("HASINEH PRICE ENGINE TEST PASSED")
print("=" * 64)
print("")

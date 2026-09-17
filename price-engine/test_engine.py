# ================================================================
# HASINEH PRICE ENGINE TEST ENGINE V3
# V299
# HISTORY + CHANGE INTEGRITY TEST
# ================================================================
#
# HASINEH MARKET
#
# این فایل فقط تست می‌کند.
# قیمت تولید نمی‌کند.
# قیمت را تغییر نمی‌دهد.
#
# ================================================================

import json
import os
import sys


PRICE_FILE = "price-engine/prices.json"


# ================================================================
# HELPERS
# ================================================================

def fail(message):
    print("")
    print("[FAIL]", message)
    print("")
    sys.exit(1)


def success(message):
    print("[PASS]", message)


# ================================================================
# START
# ================================================================

print("")
print("=" * 70)
print("HASINEH PRICE ENGINE V3")
print("V299 - HISTORY + CHANGE INTEGRITY TEST")
print("=" * 70)
print("")


# ================================================================
# CHECK FILE
# ================================================================

if not os.path.exists(PRICE_FILE):
    fail("prices.json does not exist.")

success("prices.json exists.")


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


success("prices.json is valid JSON.")


# ================================================================
# ROOT STRUCTURE
# ================================================================

if not isinstance(data, dict):
    fail("Root JSON must be an object.")

if data.get("engine") != "HASINEH PRICE ENGINE":
    fail("Invalid engine name.")

if data.get("fake_prices_allowed") is not False:
    fail("fake_prices_allowed must be false.")

if data.get("currency") != "TOMAN":
    fail("Currency must be TOMAN.")

if "prices" not in data:
    fail("prices section is missing.")

if not isinstance(data["prices"], dict):
    fail("prices must be an object.")

success("Root structure is valid.")


# ================================================================
# REQUIRED ITEMS
# ================================================================

required_items = [

    "gold_18k",
    "gold_24k",
    "gold_melted",

    "usd",
    "usdt",
    "eur",
    "gbp",
    "aed",
    "try",
    "cny",

    "coin_emami",
    "coin_half",
    "coin_quarter",

    "silver_999",
    "silver_925",

    "gold_21k_mesghal"

]


for item_name in required_items:

    if item_name not in data["prices"]:

        fail(
            "Required price item missing: "
            + item_name
        )


success(
    "All required price items exist."
)


# ================================================================
# HISTORY STRUCTURE
# ================================================================

live_count = 0
calculated_count = 0
failed_count = 0
history_count = 0


for item_name, item in data["prices"].items():

    print("")
    print("[CHECK]", item_name)

    if not isinstance(item, dict):

        fail(
            item_name
            + " must be an object."
        )


    price = item.get("price")
    previous = item.get("previous")
    change = item.get("change")
    change_percent = item.get("change_percent")
    status = item.get("status")


    # ------------------------------------------------------------
    # STATUS
    # ------------------------------------------------------------

    if status == "live":

        live_count += 1

    elif status == "calculated":

        calculated_count += 1

    else:

        failed_count += 1


    # ------------------------------------------------------------
    # PRICE
    # ------------------------------------------------------------

    if price is not None:

        if not isinstance(
            price,
            (int, float)
        ):

            fail(
                item_name
                + ": price is not numeric."
            )

        if price < 0:

            fail(
                item_name
                + ": price cannot be negative."
            )


    # ------------------------------------------------------------
    # LIVE HISTORY
    # ------------------------------------------------------------

    if status in ("live", "calculated"):

        if price is None:

            fail(
                item_name
                + ": live/calculated item has no price."
            )

        if previous is None:

            fail(
                item_name
                + ": previous price is missing."
            )

        if change is None:

            fail(
                item_name
                + ": change is missing."
            )

        if change_percent is None:

            fail(
                item_name
                + ": change_percent is missing."
            )


        if not isinstance(
            previous,
            (int, float)
        ):

            fail(
                item_name
                + ": previous is not numeric."
            )


        if not isinstance(
            change,
            (int, float)
        ):

            fail(
                item_name
                + ": change is not numeric."
            )


        if not isinstance(
            change_percent,
            (int, float)
        ):

            fail(
                item_name
                + ": change_percent is not numeric."
            )


        # --------------------------------------------------------
        # CHANGE FORMULA
        # --------------------------------------------------------

        expected_change = price - previous


        if change != expected_change:

            fail(
                item_name
                + ": change is incorrect. "
                + "Expected "
                + str(expected_change)
                + " but received "
                + str(change)
            )


        # --------------------------------------------------------
        # PERCENT FORMULA
        # --------------------------------------------------------

        if previous == 0:

            if change_percent != 0:

                fail(
                    item_name
                    + ": previous is zero but "
                    + "change_percent is not zero."
                )

        else:

            expected_percent = (
                change
                / previous
                * 100
            )


            difference = abs(
                float(change_percent)
                - expected_percent
            )


            if difference > 0.01:

                fail(
                    item_name
                    + ": change_percent is incorrect. "
                    + "Expected approximately "
                    + str(round(expected_percent, 4))
                    + " but received "
                    + str(change_percent)
                )


        history_count += 1

        print(
            "[HISTORY]",
            "previous=",
            previous,
            "change=",
            change,
            "change_percent=",
            change_percent
        )


# ================================================================
# SUMMARY
# ================================================================

print("")
print("=" * 70)
print("HASINEH PRICE ENGINE TEST SUMMARY")
print("=" * 70)

print("")
print("Total items:")
print(len(data["prices"]))

print("")
print("Live items:")
print(live_count)

print("")
print("Calculated items:")
print(calculated_count)

print("")
print("History-validated items:")
print(history_count)

print("")
print("Failed-status items:")
print(failed_count)


# ================================================================
# ENGINE HEALTH
# ================================================================

if live_count <= 0:

    fail(
        "No live price items found."
    )


if history_count <= 0:

    fail(
        "No valid history items found."
    )


summary = data.get("summary")

if not isinstance(summary, dict):

    fail(
        "summary section is missing."
    )


# ================================================================
# SUMMARY CONSISTENCY
# ================================================================

json_total = summary.get(
    "total_items"
)

json_live = summary.get(
    "live_items"
)

json_calculated = summary.get(
    "calculated_items"
)

json_failed = summary.get(
    "failed_items"
)


actual_total = len(
    data["prices"]
)


if json_total != actual_total:

    fail(
        "summary.total_items does not match prices."
    )


if json_live != live_count:

    fail(
        "summary.live_items does not match actual live items."
    )


if json_calculated != calculated_count:

    fail(
        "summary.calculated_items does not match actual calculated items."
    )


if json_failed != failed_count:

    fail(
        "summary.failed_items does not match actual failed items."
    )


success(
    "Summary counts are consistent."
)


# ================================================================
# FINAL
# ================================================================

print("")
print("=" * 70)
print("HASINEH PRICE ENGINE V3 TEST PASSED")
print("V299 HISTORY INTEGRITY: PASSED")
print("=" * 70)
print("")

sys.exit(0)

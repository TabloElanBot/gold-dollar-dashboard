# ================================================================
# HASINEH PRICE ENGINE V295
# REAL PUBLIC PRICE COLLECTOR
# ================================================================

import json
import re
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE_URL = "https://www.tgju.org"
OUTPUT_FILE = "price-engine/prices.json"
REQUEST_TIMEOUT = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
ENGLISH_DIGITS = "0123456789"


# ================================================================
# DIGITS
# ================================================================

def normalize_digits(value):
    if value is None:
        return ""

    text = str(value)

    table = str.maketrans(
        PERSIAN_DIGITS + ARABIC_DIGITS,
        ENGLISH_DIGITS + ENGLISH_DIGITS
    )

    return text.translate(table)


# ================================================================
# HTML / TEXT
# ================================================================

def clean_html_text(value):
    if value is None:
        return ""

    text = str(value)

    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text,
                  flags=re.IGNORECASE | re.DOTALL)

    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text,
                  flags=re.IGNORECASE | re.DOTALL)

    text = re.sub(r"<[^>]+>", " ", text)

    text = text.replace("&nbsp;", " ")
    text = text.replace("&comma;", ",")
    text = text.replace("&zwnj;", "")

    text = normalize_digits(text)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ================================================================
# NUMBER
# ================================================================

def clean_number(value):
    if value is None:
        return None

    text = normalize_digits(clean_html_text(value))

    text = text.replace("٬", ",")
    text = text.replace("،", ",")
    text = text.replace(" ", "")

    match = re.search(r"\d[\d,]*(?:\.\d+)?", text)

    if not match:
        return None

    number = match.group(0).replace(",", "")

    try:
        if "." in number:
            return round(float(number))
        return int(number)
    except ValueError:
        return None


# ================================================================
# RIAL -> TOMAN
# ================================================================

def rial_to_toman(value):
    if value is None:
        return None

    return round(value / 10)


# ================================================================
# FETCH
# ================================================================

def fetch_page(url):
    print("")
    print("[FETCH]", url)

    request = Request(
        url,
        headers=HEADERS
    )

    try:
        with urlopen(
            request,
            timeout=REQUEST_TIMEOUT
        ) as response:

            content = response.read()

            encoding = (
                response.headers.get_content_charset()
                or "utf-8"
            )

            page = content.decode(
                encoding,
                errors="ignore"
            )

            print("[HTTP]", response.status)
            print("[BYTES]", len(content))

            return page

    except HTTPError as error:
        print("[ERROR] HTTP:", error.code)
        return None

    except URLError as error:
        print("[ERROR] URL:", error.reason)
        return None

    except Exception as error:
        print("[ERROR] FETCH:", error)
        return None


# ================================================================
# REAL TGJU PRICE EXTRACTION
# ================================================================

def extract_current_rate(html):
    """
    TGJU pages contain the real market value next to:
    نرخ فعلی

    We intentionally DO NOT use broad JSON patterns such as:
    "price", "value", "last"

    because those can capture unrelated numbers such as 203.
    """

    if not html:
        return None

    text = clean_html_text(html)

    # ------------------------------------------------------------
    # Main method:
    # find "نرخ فعلی" and inspect the nearby text.
    # ------------------------------------------------------------

    anchors = [
        "نرخ فعلی",
        "نرخ فعلی:",
        "نرخ فعلی :",
        "نرخ فعلی::"
    ]

    for anchor in anchors:

        start = 0

        while True:

            position = text.find(anchor, start)

            if position == -1:
                break

            window = text[
                position:
                position + 180
            ]

            numbers = re.findall(
                r"\d[\d,]{3,}",
                window
            )

            for raw in numbers:

                value = clean_number(raw)

                if value is None:
                    continue

                # Reject tiny unrelated HTML numbers.
                if value < 1000:
                    continue

                print(
                    "[EXTRACT] TGJU CURRENT RATE:",
                    value
                )

                return value

            start = position + len(anchor)

    # ------------------------------------------------------------
    # Table fallback:
    # search HTML table rows containing "نرخ فعلی"
    # ------------------------------------------------------------

    rows = re.findall(
        r"<tr[^>]*>(.*?)</tr>",
        html,
        flags=re.IGNORECASE | re.DOTALL
    )

    for row in rows:

        row_text = clean_html_text(row)

        if "نرخ فعلی" not in row_text:
            continue

        numbers = re.findall(
            r"\d[\d,]{3,}",
            row_text
        )

        for raw in numbers:

            value = clean_number(raw)

            if value is None:
                continue

            if value < 1000:
                continue

            print(
                "[EXTRACT] TABLE CURRENT RATE:",
                value
            )

            return value

    print("[EXTRACT] CURRENT RATE NOT FOUND")

    return None


# ================================================================
# CREATE ITEM
# ================================================================

def create_item(name, unit, category):
    return {
        "name": name,
        "category": category,
        "price": None,
        "previous": None,
        "change": None,
        "change_percent": None,
        "unit": unit,
        "source": None,
        "status": "not_found"
    }


# ================================================================
# PARSE PROFILE
# ================================================================

def parse_item(
    symbol,
    name,
    unit,
    category
):

    item = create_item(
        name,
        unit,
        category
    )

    item["source"] = (
        BASE_URL
        + "/profile/"
        + symbol
    )

    print("")
    print(
        "[PARSER]",
        name,
        "(" + symbol + ")"
    )

    html = fetch_page(item["source"])

    if html is None:
        print("[PARSER] PAGE FAILED")
        return item

    raw_price = extract_current_rate(html)

    if raw_price is None:
        print("[PARSER] NOT FOUND")
        return item

    toman_price = rial_to_toman(raw_price)

    # ------------------------------------------------------------
    # SANITY CHECK
    # ------------------------------------------------------------

    if toman_price is None:
        print("[PARSER] INVALID PRICE")
        return item

    if toman_price <= 0:
        print("[PARSER] INVALID ZERO PRICE")
        return item

    # Never allow obviously broken tiny values.
    if toman_price < 100:
        print(
            "[PARSER] REJECTED UNREALISTIC PRICE:",
            toman_price
        )
        return item

    item["price"] = toman_price
    item["status"] = "live"

    print(
        "[PARSER] RAW RIAL:",
        raw_price
    )

    print(
        "[PARSER] TOMAN:",
        toman_price
    )

    return item


# ================================================================
# BUILD MARKET
# ================================================================

def build_market():

    prices = {}

    # ------------------------------------------------------------
    # GOLD
    # ------------------------------------------------------------

    prices["gold_18k"] = parse_item(
        "geram18",
        "طلای ۱۸ عیار",
        "تومان / گرم",
        "gold"
    )

    prices["gold_24k"] = parse_item(
        "geram24",
        "طلای ۲۴ عیار",
        "تومان / گرم",
        "gold"
    )

    prices["gold_melted"] = parse_item(
        "gold_melted",
        "طلای آب‌شده",
        "تومان",
        "gold"
    )

    # ------------------------------------------------------------
    # CURRENCY
    # ------------------------------------------------------------

    prices["usd"] = parse_item(
        "price_dollar_rl",
        "دلار آمریکا",
        "تومان",
        "currency"
    )

    prices["eur"] = parse_item(
        "price_eur",
        "یورو",
        "تومان",
        "currency"
    )

    prices["aed"] = parse_item(
        "price_aed",
        "درهم امارات",
        "تومان",
        "currency"
    )

    prices["usdt"] = parse_item(
        "price_usdt",
        "تتر",
        "تومان",
        "currency"
    )

    prices["gbp"] = parse_item(
        "price_gbp",
        "پوند انگلیس",
        "تومان",
        "currency"
    )

    prices["try"] = parse_item(
        "price_try",
        "لیر ترکیه",
        "تومان",
        "currency"
    )

    prices["cny"] = parse_item(
        "price_cny",
        "یوان چین",
        "تومان",
        "currency"
    )

    # ------------------------------------------------------------
    # COINS
    # ------------------------------------------------------------

    prices["coin_emami"] = parse_item(
        "sekee",
        "سکه امامی",
        "تومان / عدد",
        "coin"
    )

    prices["coin_half"] = parse_item(
        "sekeb",
        "نیم سکه",
        "تومان / عدد",
        "coin"
    )

    prices["coin_quarter"] = parse_item(
        "rob",
        "ربع سکه",
        "تومان / عدد",
        "coin"
    )

    # ------------------------------------------------------------
    # SILVER
    # ------------------------------------------------------------

    prices["silver_999"] = parse_item(
        "silver_999",
        "نقره ۹۹۹",
        "تومان / گرم",
        "metal"
    )

    prices["silver_925"] = parse_item(
        "silver_925",
        "نقره ۹۲۵",
        "تومان / گرم",
        "metal"
    )

    # ------------------------------------------------------------
    # 21K MESGHAL
    # CALCULATED FROM 18K
    # ------------------------------------------------------------

    gold18 = prices["gold_18k"]

    mesghal = create_item(
        "طلای ۲۱ عیار / مثقال",
        "تومان / مثقال",
        "gold"
    )

    mesghal["source"] = (
        BASE_URL
        + "/profile/geram18"
    )

    if gold18["price"] is not None:

        calculated_value = round(
            gold18["price"]
            * (21 / 18)
            * 4.6083
        )

        mesghal["price"] = calculated_value
        mesghal["status"] = "calculated"

        print("")
        print(
            "[CALCULATED] 21K MESGHAL:",
            calculated_value
        )

    prices["gold_21k_mesghal"] = mesghal

    return prices


# ================================================================
# SAVE
# ================================================================

def save_json(data):

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


# ================================================================
# MAIN
# ================================================================

def main():

    print("")
    print("=" * 64)
    print("HASINEH PRICE ENGINE V295")
    print("REAL TGJU PUBLIC PRICE COLLECTOR")
    print("=" * 64)
    print("")

    prices = build_market()

    live_count = 0
    calculated_count = 0

    for item in prices.values():

        if item["status"] == "live":
            live_count += 1

        elif item["status"] == "calculated":
            calculated_count += 1

    total_items = len(prices)

    failed_items = (
        total_items
        - live_count
        - calculated_count
    )

    # ------------------------------------------------------------
    # SAFETY:
    # if every live value disappeared, mark engine as error.
    # ------------------------------------------------------------

    if live_count > 0:
        engine_status = "live"
    else:
        engine_status = "error"

    data = {
        "engine": "HASINEH PRICE ENGINE",

        "version": "V295",

        "status": engine_status,

        "source": BASE_URL,

        "generated_at_utc":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "currency": "TOMAN",

        "fake_prices_allowed": False,

        "prices": prices,

        "summary": {
            "total_items": total_items,
            "live_items": live_count,
            "calculated_items":
                calculated_count,
            "failed_items":
                failed_items
        }
    }

    print("")
    print("=" * 64)
    print("HASINEH PRICE ENGINE V295 RESULT")
    print("=" * 64)

    print(
        "TOTAL:",
        total_items
    )

    print(
        "LIVE:",
        live_count
    )

    print(
        "CALCULATED:",
        calculated_count
    )

    print(
        "FAILED:",
        failed_items
    )

    print("=" * 64)

    save_json(data)

    print("")
    print(
        "[SUCCESS] prices.json created:"
    )

    print(
        OUTPUT_FILE
    )

    print("")

    # ------------------------------------------------------------
    # IMPORTANT:
    # Collector itself must fail if no real price is obtained.
    # This prevents bad empty data from being committed.
    # ------------------------------------------------------------

    if live_count == 0:

        print(
            "[ERROR] NO REAL LIVE PRICES FOUND."
        )

        raise SystemExit(1)

    print(
        "[ENGINE] REAL PRICE COLLECTION PASSED."
    )


# ================================================================
# START
# ================================================================

if __name__ == "__main__":
    main()

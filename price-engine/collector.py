# ================================================================
# HASINEH PRICE ENGINE V296
# REAL PRICE COLLECTOR
# ================================================================
#
# HASINEH MARKET
#
# وظیفه:
# 1. دریافت صفحات عمومی TGJU
# 2. استخراج قیمت‌های واقعی
# 3. تبدیل ریال به تومان
# 4. جلوگیری از قیمت ساختگی
# 5. تولید prices.json
#
# ================================================================

import json
import re
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


# ================================================================
# SETTINGS
# ================================================================

BASE_URL = "https://www.tgju.org"
OUTPUT_FILE = "price-engine/prices.json"
REQUEST_TIMEOUT = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}


# ================================================================
# DIGIT NORMALIZATION
# ================================================================

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
ENGLISH_DIGITS = "0123456789"


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
# HTML CLEANER
# ================================================================

def clean_html_text(value):
    if value is None:
        return ""

    text = str(value)

    text = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    text = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = text.replace("&nbsp;", " ")
    text = text.replace("&comma;", ",")
    text = text.replace("&zwnj;", "")

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ================================================================
# NUMBER CLEANER
# ================================================================

def clean_number(value):
    if value is None:
        return None

    text = normalize_digits(
        clean_html_text(value)
    )

    text = text.replace("٬", ",")
    text = text.replace("،", ",")
    text = text.replace(" ", "")

    match = re.search(
        r"\d[\d,]*",
        text
    )

    if not match:
        return None

    number = match.group(0).replace(",", "")

    try:
        return int(number)
    except ValueError:
        return None


# ================================================================
# RIAL → TOMAN
# ================================================================

def rial_to_toman(value):
    if value is None:
        return None

    return round(value / 10)


# ================================================================
# FETCH PAGE
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

            return {
                "success": True,
                "status": response.status,
                "content": page
            }

    except HTTPError as error:

        print("[ERROR] HTTP:", error.code)

        return {
            "success": False,
            "status": error.code,
            "content": ""
        }

    except URLError as error:

        print("[ERROR] URL:", error.reason)

        return {
            "success": False,
            "status": None,
            "content": ""
        }

    except Exception as error:

        print("[ERROR] FETCH:", error)

        return {
            "success": False,
            "status": None,
            "content": ""
        }


# ================================================================
# EXTRACT CURRENT RATE
# ================================================================

def extract_current_rate(html):

    text = normalize_digits(
        clean_html_text(html)
    )

    text = text.replace("٬", ",")
    text = text.replace("،", ",")

    # ------------------------------------------------------------
    # Primary target:
    # نرخ فعلی
    # ------------------------------------------------------------

    matches = list(
        re.finditer(
            r"نرخ\s*فعلی",
            text,
            flags=re.IGNORECASE
        )
    )

    for match in matches:

        window = text[
            match.end():
            match.end() + 220
        ]

        numbers = re.findall(
            r"\d[\d,]{3,}",
            window
        )

        for number_text in numbers:

            value = clean_number(
                number_text
            )

            if value is not None and value >= 1000:
                return value

    # ------------------------------------------------------------
    # Fallback:
    # table rows containing current price
    # ------------------------------------------------------------

    rows = re.findall(
        r"<tr[^>]*>(.*?)</tr>",
        html,
        flags=re.IGNORECASE | re.DOTALL
    )

    for row in rows:

        row_text = normalize_digits(
            clean_html_text(row)
        )

        row_text = row_text.replace(
            "٬",
            ","
        ).replace(
            "،",
            ","
        )

        if "نرخ فعلی" not in row_text:
            continue

        numbers = re.findall(
            r"\d[\d,]{3,}",
            row_text
        )

        for number_text in numbers:

            value = clean_number(
                number_text
            )

            if value is not None and value >= 1000:
                return value

    return None


# ================================================================
# EXTRACT LOCAL USDT MARKET PRICE
# ================================================================

def extract_usdt_local_price(html):

    # TGJU's normal Tether profile is USD-based.
    # For HASINEH we need the Iranian local USDT/IRR market.

    rows = re.findall(
        r"<tr[^>]*>(.*?)</tr>",
        html,
        flags=re.IGNORECASE | re.DOTALL
    )

    candidates = []

    for row in rows:

        row_text = normalize_digits(
            clean_html_text(row)
        )

        row_text = row_text.replace(
            "٬",
            ","
        ).replace(
            "،",
            ","
        )

        if "USDT / IRR" not in row_text.upper():
            continue

        numbers = re.findall(
            r"\d[\d,]{3,}",
            row_text
        )

        values = []

        for number_text in numbers:

            value = clean_number(
                number_text
            )

            if value is not None:
                values.append(value)

        # First numeric values after the pair are normally:
        # sell price, buy price, change, high, low...
        if values:
            candidates.append(values)

    # Prefer a realistic Iranian USDT rial price.
    for values in candidates:

        for value in values:

            if 100000 <= value <= 5000000:
                print(
                    "[USDT] LOCAL RAW RIAL:",
                    value
                )

                return rial_to_toman(
                    value
                )

    return None


# ================================================================
# FETCH TGJU PROFILE
# ================================================================

def fetch_profile(symbol):

    url = (
        BASE_URL
        + "/profile/"
        + symbol
    )

    result = fetch_page(url)

    if not result["success"]:
        return None

    html = result["content"]

    raw_price = extract_current_rate(
        html
    )

    if raw_price is None:
        return None

    return {
        "raw": raw_price,
        "toman": rial_to_toman(
            raw_price
        )
    }


# ================================================================
# FETCH LOCAL USDT
# ================================================================

def fetch_usdt_local():

    url = (
        BASE_URL
        + "/profile/crypto-tether/markets-local"
    )

    result = fetch_page(url)

    if not result["success"]:
        return None

    html = result["content"]

    return extract_usdt_local_price(
        html
    )


# ================================================================
# CREATE ITEM
# ================================================================

def create_item(
    name,
    unit,
    category
):

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
# PARSE ITEM
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

    result = fetch_profile(
        symbol
    )

    if result is None:

        print(
            "[PARSER] NOT FOUND"
        )

        return item

    toman_price = result["toman"]

    # Never accept tiny or invalid prices.
    if toman_price is None or toman_price < 100:

        print(
            "[PARSER] INVALID PRICE:",
            toman_price
        )

        return item

    item["price"] = toman_price
    item["status"] = "live"

    print(
        "[PARSER] RAW RIAL:",
        result["raw"]
    )

    print(
        "[PARSER] TOMAN:",
        toman_price
    )

    return item


# ================================================================
# PARSE LOCAL USDT
# ================================================================

def parse_usdt():

    item = create_item(
        "تتر",
        "تومان",
        "currency"
    )

    item["source"] = (
        BASE_URL
        + "/profile/crypto-tether/markets-local"
    )

    print("")
    print(
        "[PARSER] تتر (LOCAL MARKET)"
    )

    price = fetch_usdt_local()

    if price is None:

        print(
            "[PARSER] USDT NOT FOUND"
        )

        return item

    if price < 100:

        print(
            "[PARSER] USDT INVALID:",
            price
        )

        return item

    item["price"] = price
    item["status"] = "live"

    print(
        "[PARSER] USDT TOMAN:",
        price
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

    # ------------------------------------------------------------
    # MELTED GOLD
    # TGJU symbol = gold_world_futures
    # ------------------------------------------------------------

    prices["gold_melted"] = parse_item(
        "gold_world_futures",
        "طلای آب‌شده",
        "تومان / مثقال",
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

    prices["usdt"] = parse_usdt()

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

    # Correct TGJU symbol for Half Coin:
    # nim
    prices["coin_half"] = parse_item(
        "nim",
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
    #
    # Calculated from live 18K price.
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
# SAVE JSON
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
    print("HASINEH PRICE ENGINE V296")
    print("REAL PRICE COLLECTOR")
    print("=" * 64)
    print("")

    print(
        "[ENGINE] Starting real parser..."
    )

    prices = build_market()

    # ------------------------------------------------------------
    # COUNT
    # ------------------------------------------------------------

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
    # ENGINE STATUS
    # ------------------------------------------------------------

    if live_count > 0:
        engine_status = "live"
    else:
        engine_status = "error"

    # ------------------------------------------------------------
    # OUTPUT
    # ------------------------------------------------------------

    data = {

        "engine":
            "HASINEH PRICE ENGINE",

        "version":
            "V296",

        "status":
            engine_status,

        "source":
            BASE_URL,

        "generated_at_utc":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "currency":
            "TOMAN",

        "fake_prices_allowed":
            False,

        "prices":
            prices,

        "summary": {

            "total_items":
                total_items,

            "live_items":
                live_count,

            "calculated_items":
                calculated_count,

            "failed_items":
                failed_items
        }
    }

    print("")

    print(
        "[ENGINE] TOTAL ITEMS:",
        total_items
    )

    print(
        "[ENGINE] LIVE ITEMS:",
        live_count
    )

    print(
        "[ENGINE] CALCULATED ITEMS:",
        calculated_count
    )

    print(
        "[ENGINE] FAILED ITEMS:",
        failed_items
    )

    print("")

    print(
        "[OUTPUT] Creating prices.json..."
    )

    save_json(data)

    print("")

    print(
        "[SUCCESS] V296 COMPLETE"
    )

    print(
        "[OUTPUT]",
        OUTPUT_FILE
    )

    print("")

    print("=" * 64)


# ================================================================
# START
# ================================================================

if __name__ == "__main__":
    main()

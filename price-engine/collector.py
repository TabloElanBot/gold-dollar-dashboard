# ================================================================
# HASINEH PRICE ENGINE V294
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

    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ")
    text = text.replace("&comma;", ",")
    text = text.replace("&zwnj;", "")

    text = re.sub(r"\s+", " ", text)

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

    match = re.search(r"\d[\d,]*", text)

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
# EXTRACT TABLE ROWS
# ================================================================

def extract_rows(html):

    rows = []

    pattern = re.compile(
        r"<tr[^>]*>(.*?)</tr>",
        re.IGNORECASE | re.DOTALL
    )

    for row in pattern.findall(html):

        cells = re.findall(
            r"<(?:td|th)[^>]*>(.*?)</(?:td|th)>",
            row,
            re.IGNORECASE | re.DOTALL
        )

        cleaned = []

        for cell in cells:

            text = clean_html_text(cell)

            if text:
                cleaned.append(text)

        if cleaned:
            rows.append(cleaned)

    return rows


# ================================================================
# EXTRACT PROFILE PRICE
# ================================================================

def extract_profile_price(html):

    patterns = [

        r'"last"\s*:\s*"([\d,]+)"',

        r'"last_price"\s*:\s*"([\d,]+)"',

        r'"price"\s*:\s*"([\d,]+)"',

        r'"value"\s*:\s*"([\d,]+)"',

        r'data-last=["\']([\d,]+)',

        r'data-value=["\']([\d,]+)',

        r'data-price=["\']([\d,]+)'

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            html,
            re.IGNORECASE | re.DOTALL
        )

        if match:

            value = clean_number(
                match.group(1)
            )

            if value is not None:
                return value


    # ------------------------------------------------------------
    # TABLE FALLBACK
    # ------------------------------------------------------------

    rows = extract_rows(html)

    for row in rows:

        row_text = " ".join(row)

        if (
            "قیمت" in row_text
            or "زنده" in row_text
        ):

            for cell in row:

                value = clean_number(cell)

                if (
                    value is not None
                    and value > 1000
                ):
                    return value

    return None


# ================================================================
# FETCH TGJU PROFILE
# ================================================================

def fetch_profile(symbol):

    url = BASE_URL + "/profile/" + symbol

    result = fetch_page(url)

    if not result["success"]:
        return None

    html = result["content"]

    raw_price = extract_profile_price(html)

    if raw_price is None:
        return None

    return {
        "raw": raw_price,
        "toman": rial_to_toman(raw_price)
    }


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

    result = fetch_profile(symbol)

    if result is None:

        print("[PARSER] NOT FOUND")

        return item

    item["price"] = result["toman"]

    item["status"] = "live"

    print(
        "[PARSER] RAW RIAL:",
        result["raw"]
    )

    print(
        "[PARSER] TOMAN:",
        result["toman"]
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
    # ------------------------------------------------------------

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
    #
    # This is a CALCULATED value based on 18K gold.
    # It is NOT presented as a separately sourced live price.
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
            "[CALCULATED]",
            "21K MESGHAL:",
            calculated_value
        )

    prices["gold_21k_mesghal"] = mesghal


    return prices


# ================================================================
# METADATA
# ================================================================

def create_metadata():

    now = datetime.now(
        timezone.utc
    )

    return {

        "engine":
            "HASINEH PRICE ENGINE",

        "version":
            "V294",

        "mode":
            "FREE_PUBLIC_SOURCE",

        "generated_at_utc":
            now.isoformat(),

        "source":
            BASE_URL,

        "currency":
            "TOMAN",

        "rial_to_toman":
            True,

        "parser":
            "ACTIVE",

        "automatic":
            True,

        "fake_prices_allowed":
            False,

        "note":
            "Only successfully parsed public prices are accepted."
    }


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
    print("HASINEH PRICE ENGINE V294")
    print("REAL PRICE COLLECTOR")
    print("=" * 64)
    print("")

    print(
        "[ENGINE] Starting real parser..."
    )

    prices = build_market()


    # ------------------------------------------------------------
    # COUNT LIVE / CALCULATED
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
    # STATUS
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
            "V294",

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
        "[SUCCESS] V294 COMPLETE"
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

# ================================================================
# HASINEH PRICE ENGINE V292
# FREE PRICE COLLECTOR
# ================================================================
#
# HASINEH MARKET
#
# وظیفه:
# 1. اتصال به منبع عمومی
# 2. دریافت صفحه
# 3. بررسی سلامت پاسخ
# 4. آماده‌سازی ساختار استاندارد قیمت
# 5. تولید prices.json
#
# نکته:
# این نسخه هنوز هیچ قیمت ساختگی تولید نمی‌کند.
# قیمت فقط زمانی وارد سیستم می‌شود که Parser آن را
# از منبع واقعی استخراج کند.
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

SOURCE_URL = "https://www.tgju.org/"

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
# DIGIT NORMALIZER
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
# NUMBER CLEANER
# ================================================================

def clean_number(value):

    if value is None:
        return None

    text = normalize_digits(value)

    text = text.replace(",", "")
    text = text.replace("٬", "")
    text = text.replace(" ", "")
    text = text.replace(".", "")

    match = re.search(r"\d+", text)

    if not match:
        return None

    try:
        return int(match.group(0))

    except ValueError:
        return None


# ================================================================
# FETCH SOURCE
# ================================================================

def fetch_source(url):

    print("")
    print("[COLLECTOR] Connecting to public source...")
    print("[SOURCE]", url)

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

            encoding = response.headers.get_content_charset()

            if not encoding:
                encoding = "utf-8"

            page = content.decode(
                encoding,
                errors="ignore"
            )

            print("[COLLECTOR] Source response received.")
            print("[COLLECTOR] HTTP STATUS:", response.status)
            print("[COLLECTOR] BYTES:", len(content))

            return {
                "success": True,
                "status_code": response.status,
                "content": page,
                "bytes": len(content)
            }

    except HTTPError as error:

        print(
            "[ERROR] HTTP ERROR:",
            error.code
        )

        return {
            "success": False,
            "status_code": error.code,
            "content": "",
            "bytes": 0
        }

    except URLError as error:

        print(
            "[ERROR] URL ERROR:",
            error.reason
        )

        return {
            "success": False,
            "status_code": None,
            "content": "",
            "bytes": 0
        }

    except Exception as error:

        print(
            "[ERROR] CONNECTION ERROR:",
            error
        )

        return {
            "success": False,
            "status_code": None,
            "content": "",
            "bytes": 0
        }


# ================================================================
# SOURCE HEALTH CHECK
# ================================================================

def check_source(source):

    if not source["success"]:

        return {
            "online": False,
            "message": "SOURCE_UNAVAILABLE"
        }

    if source["status_code"] != 200:

        return {
            "online": False,
            "message": "HTTP_STATUS_NOT_200"
        }

    if source["bytes"] < 500:

        return {
            "online": False,
            "message": "RESPONSE_TOO_SMALL"
        }

    return {
        "online": True,
        "message": "SOURCE_OK"
    }


# ================================================================
# PRICE ITEM
# ================================================================

def create_price_item(
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
        "status": "waiting_parser"
    }


# ================================================================
# MARKET STRUCTURE
# ================================================================

def create_market_structure():

    return {

        "gold_18": create_price_item(
            "طلای ۱۸ عیار",
            "تومان / گرم",
            "gold"
        ),

        "gold_24": create_price_item(
            "طلای ۲۴ عیار",
            "تومان / گرم",
            "gold"
        ),

        "mesghal_21": create_price_item(
            "مثقال طلای ۲۱ عیار",
            "تومان / مثقال",
            "gold"
        ),

        "coin_emami": create_price_item(
            "سکه امامی",
            "تومان / عدد",
            "coin"
        ),

        "coin_half": create_price_item(
            "نیم سکه",
            "تومان / عدد",
            "coin"
        ),

        "coin_quarter": create_price_item(
            "ربع سکه",
            "تومان / عدد",
            "coin"
        ),

        "silver": create_price_item(
            "نقره",
            "تومان / گرم",
            "metal"
        ),

        "usd": create_price_item(
            "دلار آمریکا",
            "تومان",
            "currency"
        ),

        "eur": create_price_item(
            "یورو",
            "تومان",
            "currency"
        ),

        "aed": create_price_item(
            "درهم امارات",
            "تومان",
            "currency"
        ),

        "usdt": create_price_item(
            "تتر",
            "تومان",
            "crypto"
        )
    }


# ================================================================
# ENGINE META
# ================================================================

def create_metadata(source_health):

    now = datetime.now(
        timezone.utc
    )

    return {

        "engine": "HASINEH PRICE ENGINE",

        "version": "V292",

        "mode": "FREE_PUBLIC_SOURCE",

        "generated_at_utc": now.isoformat(),

        "source": SOURCE_URL,

        "source_health": source_health,

        "currency": "TOMAN",

        "parser": "NOT_ACTIVE",

        "automatic": True,

        "fake_prices_allowed": False
    }


# ================================================================
# BUILD DATA
# ================================================================

def build_data(source):

    health = check_source(
        source
    )

    prices = create_market_structure()

    for key in prices:

        prices[key]["source"] = SOURCE_URL

        if health["online"]:

            prices[key]["status"] = (
                "waiting_for_parser"
            )

        else:

            prices[key]["status"] = (
                "source_unavailable"
            )

    return {

        "meta": create_metadata(
            health
        ),

        "prices": prices
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
    print("HASINEH PRICE ENGINE V292")
    print("FREE PRICE COLLECTOR")
    print("=" * 64)

    source = fetch_source(
        SOURCE_URL
    )

    print("")
    print("[CHECK] Checking source health...")

    health = check_source(
        source
    )

    print(
        "[CHECK]",
        health["message"]
    )

    print("")
    print("[ENGINE] Building market structure...")

    data = build_data(
        source
    )

    print(
        "[ENGINE] Market items:",
        len(data["prices"])
    )

    print("")
    print("[OUTPUT] Creating prices.json...")

    save_json(
        data
    )

    print("")
    print("[SUCCESS] HASINEH PRICE ENGINE V292 READY")

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

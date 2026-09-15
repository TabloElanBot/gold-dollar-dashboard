# ================================================================
# HASINEH PRICE ENGINE V293
# REAL PRICE PARSER
# ================================================================
#
# HASINEH MARKET
#
# وظیفه:
# 1. دریافت صفحات عمومی TGJU
# 2. استخراج قیمت واقعی
# 3. تبدیل ریال به تومان
# 4. استخراج تغییرات
# 5. تولید prices.json
#
# بدون قیمت ساختگی
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
# PUBLIC TGJU PAGES
# ================================================================

SOURCE_PAGES = {
    "gold": BASE_URL + "/gold-chart",
    "currency": BASE_URL + "/currency",
    "coin": BASE_URL + "/coin",
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
# HTML TEXT CLEANER
# ================================================================

def clean_html_text(value):

    if value is None:
        return ""

    text = str(value)

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = text.replace(
        "&nbsp;",
        " "
    )

    text = text.replace(
        "&comma;",
        ","
    )

    text = text.replace(
        "&zwnj;",
        ""
    )

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

    text = text.replace(
        "٬",
        ","
    )

    text = text.replace(
        "،",
        ","
    )

    text = text.replace(
        " ",
        ""
    )

    # حذف واحدها و کاراکترهای غیرعددی
    match = re.search(
        r"\d[\d,]*",
        text
    )

    if not match:
        return None

    number = match.group(0)

    number = number.replace(
        ",",
        ""
    )

    try:

        return int(number)

    except ValueError:

        return None


# ================================================================
# RIAL -> TOMAN
# ================================================================

def rial_to_toman(value):

    if value is None:
        return None

    return round(
        value / 10
    )


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

            print(
                "[HTTP]",
                response.status
            )

            print(
                "[BYTES]",
                len(content)
            )

            return {
                "success": True,
                "status": response.status,
                "content": page
            }

    except HTTPError as error:

        print(
            "[ERROR] HTTP:",
            error.code
        )

        return {
            "success": False,
            "status": error.code,
            "content": ""
        }

    except URLError as error:

        print(
            "[ERROR] URL:",
            error.reason
        )

        return {
            "success": False,
            "status": None,
            "content": ""
        }

    except Exception as error:

        print(
            "[ERROR] FETCH:",
            error
        )

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
        re.IGNORECASE |
        re.DOTALL
    )

    for row in pattern.findall(html):

        cells = re.findall(
            r"<(?:td|th)[^>]*>(.*?)</(?:td|th)>",
            row,
            re.IGNORECASE |
            re.DOTALL
        )

        cleaned = []

        for cell in cells:

            text = clean_html_text(
                cell
            )

            if text:
                cleaned.append(
                    text
                )

        if cleaned:
            rows.append(
                cleaned
            )

    return rows


# ================================================================
# FIND PRICE BY KEY
# ================================================================

def find_price_by_key(
    html,
    key
):

    # روش اصلی:
    # پیدا کردن ردیف/بلوک مربوط به شناسه TGJU

    patterns = [

        rf'id=["\']{re.escape(key)}["\'][^>]*>(.*?)</',
        
        rf'data-symbol=["\']{re.escape(key)}["\'][^>]*>(.*?)</',

        rf'data-symbol=["\']{re.escape(key)}["\'][^>]*.*?'
        rf'(?:data-value|data-price)=["\']([^"\']+)',

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            html,
            re.IGNORECASE |
            re.DOTALL
        )

        if match:

            value = clean_number(
                match.group(1)
            )

            if value is not None:
                return value

    return None


# ================================================================
# FIND PRICE FROM PROFILE PAGE
# ================================================================

def parse_profile(
    key
):

    url = (
        BASE_URL
        + "/profile/"
        + key
    )

    result = fetch_page(
        url
    )

    if not result["success"]:
        return None

    html = result["content"]

    # الگوهای رایج TGJU
    patterns = [

        r'"last":"([\d,]+)"',

        r'"last_price":"([\d,]+)"',

        r'"price":"([\d,]+)"',

        r'"value":"([\d,]+)"',

        r'data-last=["\']([\d,]+)',

        r'data-value=["\']([\d,]+)',

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            html,
            re.IGNORECASE
        )

        if match:

            value = clean_number(
                match.group(1)
            )

            if value is not None:

                return {
                    "raw": value,
                    "toman": rial_to_toman(
                        value
                    )
                }

    # جستجوی جدول
    rows = extract_rows(
        html
    )

    for row in rows:

        row_text = " ".join(
            row
        )

        if (
            "قیمت" in row_text
            or "زنده" in row_text
        ):

            for cell in row:

                value = clean_number(
                    cell
                )

                if (
                    value is not None
                    and value > 1000
                ):

                    return {
                        "raw": value,
                        "toman": rial_to_toman(
                            value
                        )
                    }

    return None


# ================================================================
# MARKET ITEM
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
# PARSE MARKET ITEM
# ================================================================

def parse_item(
    key,
    name,
    unit,
    category,
    source_page
):

    item = create_item(
        name,
        unit,
        category
    )

    item["source"] = (
        BASE_URL
        + "/profile/"
        + key
    )

    print("")
    print(
        "[PARSER]",
        name,
        "(" + key + ")"
    )

    result = parse_profile(
        key
    )

    if result is None:

        print(
            "[PARSER] NOT FOUND"
        )

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

    prices["gold_18"] = parse_item(
        "geram18",
        "طلای ۱۸ عیار",
        "تومان / گرم",
        "gold",
        SOURCE_PAGES["gold"]
    )

    prices["gold_24"] = parse_item(
        "geram24",
        "طلای ۲۴ عیار",
        "تومان / گرم",
        "gold",
        SOURCE_PAGES["gold"]
    )

    # ------------------------------------------------------------
    # CURRENCY
    # ------------------------------------------------------------

    prices["usd"] = parse_item(
        "price_dollar_rl",
        "دلار آمریکا",
        "تومان",
        "currency",
        SOURCE_PAGES["currency"]
    )

    prices["eur"] = parse_item(
        "price_eur",
        "یورو",
        "تومان",
        "currency",
        SOURCE_PAGES["currency"]
    )

    prices["aed"] = parse_item(
        "price_aed",
        "درهم امارات",
        "تومان",
        "currency",
        SOURCE_PAGES["currency"]
    )

    # ------------------------------------------------------------
    # EXTRA CURRENCIES
    # ------------------------------------------------------------

    prices["gbp"] = parse_item(
        "price_gbp",
        "پوند انگلیس",
        "تومان",
        "currency",
        SOURCE_PAGES["currency"]
    )

    prices["try"] = parse_item(
        "price_try",
        "لیر ترکیه",
        "تومان",
        "currency",
        SOURCE_PAGES["currency"]
    )

    prices["cny"] = parse_item(
        "price_cny",
        "یوان چین",
        "تومان",
        "currency",
        SOURCE_PAGES["currency"]
    )

    # ------------------------------------------------------------
    # COIN
    # ------------------------------------------------------------

    prices["coin_emami"] = parse_item(
        "sekee",
        "سکه امامی",
        "تومان / عدد",
        "coin",
        SOURCE_PAGES["coin"]
    )

    prices["coin_half"] = parse_item(
        "sekeb",
        "نیم سکه",
        "تومان / عدد",
        "coin",
        SOURCE_PAGES["coin"]
    )

    prices["coin_quarter"] = parse_item(
        "sekeb",
        "ربع سکه",
        "تومان / عدد",
        "coin",
        SOURCE_PAGES["coin"]
    )

    # ------------------------------------------------------------
    # SILVER
    # ------------------------------------------------------------

    prices["silver"] = parse_item(
        "silver_925",
        "نقره ۹۲۵",
        "تومان / گرم",
        "metal",
        SOURCE_PAGES["gold"]
    )

    return prices


# ================================================================
# META
# ================================================================

def create_metadata():

    now = datetime.now(
        timezone.utc
    )

    return {

        "engine":
            "HASINEH PRICE ENGINE",

        "version":
            "V293",

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
            "Only successfully parsed public prices "
            "are accepted."
    }


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

    print(
        "HASINEH PRICE ENGINE V293"
    )

    print(
        "REAL PRICE PARSER"
    )

    print("=" * 64)

    print("")
    print(
        "[ENGINE] Starting real parser..."
    )

    prices = build_market()

    live_count = 0

    for key, item in prices.items():

        if item["status"] == "live":

            live_count += 1

    data = {

        "meta":
            create_metadata(),

        "prices":
            prices,

        "summary": {

            "total_items":
                len(prices),

            "live_items":
                live_count,

            "failed_items":
                len(prices)
                - live_count
        }
    }

    print("")
    print(
        "[ENGINE] TOTAL ITEMS:",
        len(prices)
    )

    print(
        "[ENGINE] LIVE ITEMS:",
        live_count
    )

    print(
        "[ENGINE] FAILED ITEMS:",
        len(prices)
        - live_count
    )

    print("")
    print(
        "[OUTPUT] Creating prices.json..."
    )

    save_json(
        data
    )

    print("")
    print(
        "[SUCCESS] V293 COMPLETE"
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

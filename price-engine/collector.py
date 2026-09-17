# ============================================================
# HASINEH PRICE ENGINE V297
# REAL PRICE COLLECTOR + PRICE HISTORY + CHANGE DETECTION
# ============================================================

import json
import re
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://www.tgju.org"
OUTPUT_FILE = "price-engine/prices.json"
TIMEOUT = 20


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
}


# ------------------------------------------------------------
# DIGIT NORMALIZATION
# ------------------------------------------------------------

def normalize_digits(value):
    if value is None:
        return ""

    text = str(value)

    replacements = {
        "۰": "0",
        "۱": "1",
        "۲": "2",
        "۳": "3",
        "۴": "4",
        "۵": "5",
        "۶": "6",
        "۷": "7",
        "۸": "8",
        "۹": "9",
        "٠": "0",
        "١": "1",
        "٢": "2",
        "٣": "3",
        "٤": "4",
        "٥": "5",
        "٦": "6",
        "٧": "7",
        "٨": "8",
        "٩": "9",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


# ------------------------------------------------------------
# HTML CLEANING
# ------------------------------------------------------------

def clean_html(html):
    if not html:
        return ""

    text = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    text = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    text = re.sub(r"<[^>]+>", " ", text)

    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")

    text = re.sub(r"\s+", " ", text)

    return normalize_digits(text).strip()


# ------------------------------------------------------------
# NUMBER CLEANING
# ------------------------------------------------------------

def clean_number(value):
    if value is None:
        return None

    text = normalize_digits(value)

    text = (
        text.replace(",", "")
        .replace("٬", "")
        .replace("،", "")
        .replace(" ", "")
    )

    match = re.search(r"-?\d+(?:\.\d+)?", text)

    if not match:
        return None

    try:
        number = float(match.group(0))

        if number.is_integer():
            return int(number)

        return number

    except Exception:
        return None


def rial_to_toman(value):
    if value is None:
        return None

    return round(value / 10)


# ------------------------------------------------------------
# FETCH
# ------------------------------------------------------------

def fetch_page(url):
    request = Request(url, headers=HEADERS)

    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            content = response.read().decode("utf-8", errors="ignore")

            return {
                "ok": True,
                "status": response.status,
                "content": content,
                "url": url,
            }

    except HTTPError as exc:
        return {
            "ok": False,
            "status": exc.code,
            "content": "",
            "url": url,
            "error": f"HTTP {exc.code}",
        }

    except URLError as exc:
        return {
            "ok": False,
            "status": None,
            "content": "",
            "url": url,
            "error": f"URL Error: {exc.reason}",
        }

    except Exception as exc:
        return {
            "ok": False,
            "status": None,
            "content": "",
            "url": url,
            "error": str(exc),
        }


# ------------------------------------------------------------
# CURRENT RATE EXTRACTION
# ------------------------------------------------------------

def extract_current_rate(html):
    text = clean_html(html)

    if not text:
        return None

    # Primary method: text around "نرخ فعلی"
    patterns = [
        r"نرخ فعلی.{0,250}?([\d۰-۹][\d۰-۹,٬،\s]*)",
        r"نرخ فعلی.{0,120}?([\d۰-۹][\d۰-۹,٬،]*)",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)

        for match in matches:
            value = clean_number(match)

            if value is not None and value > 0:
                return value

    # Secondary method: nearby realistic numbers
    index = text.find("نرخ فعلی")

    if index >= 0:
        area = text[index:index + 600]

        numbers = re.findall(
            r"[\d۰-۹][\d۰-۹,٬،\s]{2,}",
            area
        )

        candidates = []

        for item in numbers:
            value = clean_number(item)

            if value is not None and value > 0:
                candidates.append(value)

        if candidates:
            return candidates[0]

    return None


# ------------------------------------------------------------
# USDT LOCAL MARKET
# ------------------------------------------------------------

def extract_usdt_local_price(html):
    text = clean_html(html)

    if not text:
        return None

    lines = re.split(r"\s{2,}", text)

    candidates = []

    for line in lines:
        upper = line.upper()

        if "USDT" not in upper:
            continue

        if "IRR" not in upper and "تومان" not in line:
            continue

        numbers = re.findall(
            r"[\d۰-۹][\d۰-۹,٬،\s]{2,}",
            line
        )

        for number in numbers:
            value = clean_number(number)

            if value is None:
                continue

            # USDT/IRR is normally much larger than ordinary decimal data.
            if 1000000 <= value <= 5000000000:
                candidates.append(value)

    if not candidates:
        return None

    # Use the smallest realistic market price candidate.
    # This helps avoid volume / unrelated large values.
    selected = min(candidates)

    return rial_to_toman(selected)


# ------------------------------------------------------------
# PROFILE FETCH
# ------------------------------------------------------------

def fetch_profile(symbol):
    url = f"{BASE_URL}/profile/{symbol}"

    result = fetch_page(url)

    if not result["ok"]:
        return {
            "raw": None,
            "toman": None,
            "url": url,
            "error": result.get("error"),
        }

    raw = extract_current_rate(result["content"])

    if raw is None:
        return {
            "raw": None,
            "toman": None,
            "url": url,
            "error": "Current rate not found",
        }

    toman = rial_to_toman(raw)

    return {
        "raw": raw,
        "toman": toman,
        "url": url,
        "error": None,
    }


# ------------------------------------------------------------
# USDT FETCH
# ------------------------------------------------------------

def fetch_usdt_local():
    url = f"{BASE_URL}/profile/crypto-tether/markets-local"

    result = fetch_page(url)

    if not result["ok"]:
        return {
            "raw": None,
            "toman": None,
            "url": url,
            "error": result.get("error"),
        }

    toman = extract_usdt_local_price(result["content"])

    if toman is None:
        return {
            "raw": None,
            "toman": None,
            "url": url,
            "error": "USDT local price not found",
        }

    return {
        "raw": toman * 10,
        "toman": toman,
        "url": url,
        "error": None,
    }


# ------------------------------------------------------------
# LOAD PREVIOUS PRICES
# ------------------------------------------------------------

def load_previous_prices():
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as file:
            old_data = json.load(file)

        prices = old_data.get("prices", {})

        if isinstance(prices, dict):
            return prices

    except Exception:
        pass

    return {}


# ------------------------------------------------------------
# HISTORY / CHANGE CALCULATION
# ------------------------------------------------------------

def get_previous_price(previous_prices, key):
    old_item = previous_prices.get(key)

    if old_item is None:
        return None

    # Old format support
    if isinstance(old_item, (int, float)):
        if old_item >= 0:
            return old_item

        return None

    # Current object format
    if isinstance(old_item, dict):
        old_price = old_item.get("price")

        if isinstance(old_price, (int, float)):
            if old_price >= 0:
                return old_price

    return None


def apply_history(item, previous_prices, key):
    current = item.get("price")

    old_price = get_previous_price(previous_prices, key)

    item["previous"] = None
    item["change"] = None
    item["change_percent"] = None

    # No valid current price.
    if not isinstance(current, (int, float)):
        return item

    # No previous valid price.
    if old_price is None:
        return item

    if old_price < 0:
        return item

    change = current - old_price

    if old_price == 0:
        change_percent = None
    else:
        change_percent = round((change / old_price) * 100, 4)

    item["previous"] = old_price
    item["change"] = change
    item["change_percent"] = change_percent

    return item


# ------------------------------------------------------------
# ITEM CREATION
# ------------------------------------------------------------

def create_item(name, category, unit, source):
    return {
        "name": name,
        "category": category,
        "price": None,
        "previous": None,
        "change": None,
        "change_percent": None,
        "unit": unit,
        "source": source,
        "status": "not_found",
    }


def parse_item(name, category, unit, symbol, previous_prices, key):
    source = f"{BASE_URL}/profile/{symbol}"

    item = create_item(
        name=name,
        category=category,
        unit=unit,
        source=source,
    )

    result = fetch_profile(symbol)

    toman_price = result.get("toman")

    if isinstance(toman_price, (int, float)) and toman_price >= 100:
        item["price"] = toman_price
        item["status"] = "live"

    apply_history(item, previous_prices, key)

    return item


def parse_usdt(previous_prices, key):
    source = f"{BASE_URL}/profile/crypto-tether/markets-local"

    item = create_item(
        name="تتر",
        category="currency",
        unit="تومان",
        source=source,
    )

    result = fetch_usdt_local()

    toman_price = result.get("toman")

    if isinstance(toman_price, (int, float)) and toman_price >= 100:
        item["price"] = toman_price
        item["status"] = "live"

    apply_history(item, previous_prices, key)

    return item


# ------------------------------------------------------------
# MARKET BUILD
# ------------------------------------------------------------

def build_market(previous_prices):
    prices = {}

    prices["gold_18k"] = parse_item(
        "طلای ۱۸ عیار",
        "gold",
        "تومان / گرم",
        "geram18",
        previous_prices,
        "gold_18k",
    )

    prices["gold_24k"] = parse_item(
        "طلای ۲۴ عیار",
        "gold",
        "تومان / گرم",
        "geram24",
        previous_prices,
        "gold_24k",
    )

    prices["gold_melted"] = parse_item(
        "طلای آب‌شده",
        "gold",
        "تومان / مثقال",
        "gold_world_futures",
        previous_prices,
        "gold_melted",
    )

    prices["usd"] = parse_item(
        "دلار آمریکا",
        "currency",
        "تومان",
        "price_dollar_rl",
        previous_prices,
        "usd",
    )

    prices["eur"] = parse_item(
        "یورو",
        "currency",
        "تومان",
        "price_eur",
        previous_prices,
        "eur",
    )

    prices["aed"] = parse_item(
        "درهم امارات",
        "currency",
        "تومان",
        "price_aed",
        previous_prices,
        "aed",
    )

    prices["usdt"] = parse_usdt(
        previous_prices,
        "usdt",
    )

    prices["gbp"] = parse_item(
        "پوند انگلیس",
        "currency",
        "تومان",
        "price_gbp",
        previous_prices,
        "gbp",
    )

    prices["try"] = parse_item(
        "لیر ترکیه",
        "currency",
        "تومان",
        "price_try",
        previous_prices,
        "try",
    )

    prices["cny"] = parse_item(
        "یوان چین",
        "currency",
        "تومان",
        "price_cny",
        previous_prices,
        "cny",
    )

    prices["coin_emami"] = parse_item(
        "سکه امامی",
        "coin",
        "تومان / عدد",
        "sekee",
        previous_prices,
        "coin_emami",
    )

    prices["coin_half"] = parse_item(
        "نیم سکه",
        "coin",
        "تومان / عدد",
        "nim",
        previous_prices,
        "coin_half",
    )

    prices["coin_quarter"] = parse_item(
        "ربع سکه",
        "coin",
        "تومان / عدد",
        "rob",
        previous_prices,
        "coin_quarter",
    )

    prices["silver_999"] = parse_item(
        "نقره ۹۹۹",
        "metal",
        "تومان / گرم",
        "silver_999",
        previous_prices,
        "silver_999",
    )

    prices["silver_925"] = parse_item(
        "نقره ۹۲۵",
        "metal",
        "تومان / گرم",
        "silver_925",
        previous_prices,
        "silver_925",
    )

    # --------------------------------------------------------
    # 21K MESGHAL
    # --------------------------------------------------------

    mesghal = create_item(
        name="طلای ۲۱ عیار / مثقال",
        category="gold",
        unit="تومان / مثقال",
        source=f"{BASE_URL}/profile/geram18",
    )

    gold18_price = prices["gold_18k"].get("price")

    if isinstance(gold18_price, (int, float)) and gold18_price > 0:
        mesghal["price"] = round(
            gold18_price * (21 / 18) * 4.6083
        )

        mesghal["status"] = "calculated"

    apply_history(
        mesghal,
        previous_prices,
        "gold_21k_mesghal",
    )

    prices["gold_21k_mesghal"] = mesghal

    return prices


# ------------------------------------------------------------
# SAVE JSON
# ------------------------------------------------------------

def save_json(data):
    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():
    print("=" * 60)
    print("HASINEH PRICE ENGINE V297")
    print("REAL PRICE COLLECTOR")
    print("PRICE HISTORY + CHANGE DETECTION")
    print("=" * 60)

    print("")
    print("Loading previous prices...")

    previous_prices = load_previous_prices()

    if previous_prices:
        print(
            f"Previous price records found: "
            f"{len(previous_prices)}"
        )
    else:
        print("No previous price history found.")

    print("")
    print("Collecting live market prices...")
    print("Source:", BASE_URL)
    print("")

    prices = build_market(previous_prices)

    live_count = 0
    calculated_count = 0
    failed_count = 0

    for key, item in prices.items():
        status = item.get("status")

        if status == "live":
            live_count += 1

        elif status == "calculated":
            calculated_count += 1

        else:
            failed_count += 1

        price = item.get("price")
        previous = item.get("previous")
        change = item.get("change")
        change_percent = item.get("change_percent")

        print(
            f"{key}: "
            f"price={price} | "
            f"previous={previous} | "
            f"change={change} | "
            f"change_percent={change_percent} | "
            f"status={status}"
        )

    total_items = len(prices)

    engine_status = (
        "live"
        if live_count > 0
        else "error"
    )

    data = {
        "engine": "HASINEH PRICE ENGINE",
        "version": "V297",
        "status": engine_status,
        "source": BASE_URL,
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "currency": "TOMAN",
        "fake_prices_allowed": False,
        "prices": prices,
        "summary": {
            "total_items": total_items,
            "live_items": live_count,
            "calculated_items": calculated_count,
            "failed_items": failed_count,
        },
    }

    save_json(data)

    print("")
    print("=" * 60)
    print("HASINEH PRICE ENGINE V297 COMPLETE")
    print("=" * 60)
    print(f"Total items:      {total_items}")
    print(f"Live items:       {live_count}")
    print(f"Calculated items: {calculated_count}")
    print(f"Failed items:     {failed_count}")
    print("Fake data:        DISABLED")
    print("History:          ENABLED")
    print("Change detection: ENABLED")
    print("=" * 60)

    if live_count == 0:
        print("ERROR: No live prices collected.")
        sys.exit(1)


if __name__ == "__main__":
    main()

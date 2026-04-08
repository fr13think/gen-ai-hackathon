from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from langchain_core.tools import tool


BUSINESS_PROFILE = {
    "nama": "Kopi Nusantara",
    "kota": "Bandung",
    "jenis_usaha": "Coffee shop and retail beans business",
    "jam_operasional": "08.00-22.00 WIB",
}

INVENTORY_DATA = {
    "biji kopi arabika": {
        "stok": 2,
        "unit": "kg",
        "status": "Kritis",
        "reorder_point": 5,
        "lead_time_days": 3,
        "supplier": "PT Kopi Priangan",
    },
    "gula aren": {
        "stok": 15,
        "unit": "kg",
        "status": "Aman",
        "reorder_point": 7,
        "lead_time_days": 2,
        "supplier": "CV Manis Alam",
    },
    "susu fresh": {
        "stok": 5,
        "unit": "liter",
        "status": "Kritis",
        "reorder_point": 8,
        "lead_time_days": 1,
        "supplier": "Koperasi Susu Sejahtera",
    },
    "cup 16 oz": {
        "stok": 120,
        "unit": "pcs",
        "status": "Aman",
        "reorder_point": 80,
        "lead_time_days": 2,
        "supplier": "PT Kemasan Jaya",
    },
}

SALES_DATA = [
    {"produk": "Es Kopi Aren", "terjual_hari_ini": 42, "pendapatan": 756000, "margin": 0.62},
    {"produk": "Cappuccino", "terjual_hari_ini": 26, "pendapatan": 520000, "margin": 0.58},
    {"produk": "Manual Brew", "terjual_hari_ini": 14, "pendapatan": 420000, "margin": 0.66},
    {"produk": "Kopi Susu 1L", "terjual_hari_ini": 8, "pendapatan": 520000, "margin": 0.49},
]

TODAY_ACTIONS = [
    "Restock arabica beans before Friday to protect weekend sales.",
    "Launch an iced coffee bundle with pastry between 15.00 and 18.00 to increase repeat orders.",
    "Contact the fresh milk supplier now because current stock covers only about one normal business day.",
]

BUSINESS_TIMEZONE = ZoneInfo(os.getenv("BUSINESS_TIMEZONE", "Asia/Jakarta"))
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "").strip()


def _find_inventory_item(keyword: str) -> tuple[str, dict[str, Any]] | None:
    normalized = keyword.strip().lower()
    for item_name, item in INVENTORY_DATA.items():
        if normalized in item_name.lower() or item_name.lower() in normalized:
            return item_name, item
    return None


def _normalize_schedule_text(text: str) -> str:
    cleaned = text.strip().strip("'\"")
    if not cleaned:
        return "Operations meeting"
    return cleaned[0].upper() + cleaned[1:]


def _resolve_schedule_window(waktu: str) -> tuple[datetime, datetime]:
    lowered = waktu.strip().lower()
    now = datetime.now(BUSINESS_TIMEZONE)
    base_date = now.date()

    if "tomorrow" in lowered or "besok" in lowered:
        base_date = base_date + timedelta(days=1)

    hour = 9
    minute = 0
    duration_minutes = 30

    if "morning" in lowered or "pagi" in lowered:
        hour = 9
    elif "afternoon" in lowered or "siang" in lowered:
        hour = 14
    elif "evening" in lowered or "sore" in lowered:
        hour = 18

    match = re.search(r"(\d{1,2})[.:](\d{2})", lowered)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))

    start = datetime(
        year=base_date.year,
        month=base_date.month,
        day=base_date.day,
        hour=hour,
        minute=minute,
        tzinfo=BUSINESS_TIMEZONE,
    )
    end = start + timedelta(minutes=duration_minutes)
    return start, end


def _create_google_calendar_event(activity: str, waktu: str) -> str:
    if not CALENDAR_ID:
        raise RuntimeError("GOOGLE_CALENDAR_ID is not configured.")

    start, end = _resolve_schedule_window(waktu)
    service = build("calendar", "v3", cache_discovery=False)
    event_body = {
        "summary": activity,
        "description": "Created by UMKM AI Copilot.",
        "start": {
            "dateTime": start.isoformat(),
            "timeZone": str(BUSINESS_TIMEZONE),
        },
        "end": {
            "dateTime": end.isoformat(),
            "timeZone": str(BUSINESS_TIMEZONE),
        },
    }
    created = service.events().insert(calendarId=CALENDAR_ID, body=event_body).execute()
    event_link = created.get("htmlLink", "")
    pretty_start = start.strftime("%A, %d %b %Y at %H:%M")
    if event_link:
        return f"{activity} has been scheduled for {pretty_start} WIB. Calendar event created successfully: {event_link}"
    return f"{activity} has been scheduled for {pretty_start} WIB. Calendar event created successfully."


def get_dashboard_snapshot() -> dict[str, Any]:
    omzet_hari_ini = sum(item["pendapatan"] for item in SALES_DATA)
    produk_terlaris = max(SALES_DATA, key=lambda item: item["terjual_hari_ini"])
    stok_kritis = [
        {
            "nama": name,
            "stok": f'{item["stok"]} {item["unit"]}',
            "supplier": item["supplier"],
        }
        for name, item in INVENTORY_DATA.items()
        if item["status"] == "Kritis"
    ]
    quick_actions = [
        "Create a restock plan for today's critical inventory",
        "Summarize today's sales performance and recommend actions",
        "Schedule a supplier meeting for tomorrow morning",
        "Create a promo idea for the highest-margin product",
    ]
    return {
        "profile": BUSINESS_PROFILE,
        "metrics": {
            "omzet_hari_ini": omzet_hari_ini,
            "total_transaksi_estimasi": 124,
            "produk_terlaris": produk_terlaris["produk"],
            "stok_kritis_count": len(stok_kritis),
        },
        "stok_kritis": stok_kritis,
        "penjualan": SALES_DATA,
        "rekomendasi_hari_ini": TODAY_ACTIONS,
        "quick_actions": quick_actions,
        "generated_at": datetime.now().isoformat(),
    }


@tool
def cek_stok_barang(nama_barang: str) -> str:
    """Use this tool to check inventory level, stock status, and related supplier."""
    matched = _find_inventory_item(nama_barang)
    if not matched:
        return (
            f"Item '{nama_barang}' was not found. "
            f"Available items: {', '.join(INVENTORY_DATA.keys())}."
        )

    item_name, item = matched
    return (
        f"Current stock for {item_name} is {item['stok']} {item['unit']} with status {item['status']}. "
        f"The reorder point is {item['reorder_point']} {item['unit']} and the main supplier is {item['supplier']}."
    )


@tool
def rekomendasi_restock_hari_ini() -> str:
    """Use this tool to create today's priority restock recommendation based on critical inventory."""
    priorities = []
    for item_name, item in INVENTORY_DATA.items():
        if item["stok"] <= item["reorder_point"]:
            priorities.append(
                f"{item_name}: stock {item['stok']} {item['unit']}, "
                f"safe minimum {item['reorder_point']} {item['unit']}, "
                f"supplier {item['supplier']}, lead time {item['lead_time_days']} days"
            )

    if not priorities:
        return "All inventory is above the reorder point. No urgent restock is needed today."

    return (
        "Today's restock priorities:\n- "
        + "\n- ".join(priorities)
        + "\nRecommendation: prioritize critical items first to keep tomorrow's operations safe."
    )


@tool
def ringkasan_operasional_hari_ini() -> str:
    """Use this tool to summarize today's sales performance, critical inventory, and operating actions."""
    snapshot = get_dashboard_snapshot()
    metrics = snapshot["metrics"]
    return (
        f"Operational summary for {date.today().isoformat()}: today's revenue is Rp{metrics['omzet_hari_ini']:,}, "
        f"estimated transactions are {metrics['total_transaksi_estimasi']}, the top product is {metrics['produk_terlaris']}, "
        f"and there are {metrics['stok_kritis_count']} critical inventory items. "
        f"Top actions: {'; '.join(snapshot['rekomendasi_hari_ini'])}"
    )


@tool
def analisis_produk_terlaris() -> str:
    """Use this tool to analyze the best-selling product and quick promotion opportunities."""
    sorted_products = sorted(SALES_DATA, key=lambda item: item["terjual_hari_ini"], reverse=True)
    top_product = sorted_products[0]
    high_margin = max(SALES_DATA, key=lambda item: item["margin"])
    return (
        f"Today's best-selling product is {top_product['produk']} with {top_product['terjual_hari_ini']} servings "
        f"and revenue of Rp{top_product['pendapatan']:,}. "
        f"The highest-margin product is {high_margin['produk']} ({int(high_margin['margin'] * 100)}%). "
        f"Recommendation: push a bundle around {top_product['produk']} and upsell {high_margin['produk']} during the afternoon peak."
    )


@tool
def buat_jadwal_kalender(kegiatan: str, waktu: str) -> str:
    """Use this tool to create a schedule for meetings, supplier follow-up, or operating activities."""
    activity = _normalize_schedule_text(kegiatan)
    schedule_time = _normalize_schedule_text(waktu)
    try:
        return _create_google_calendar_event(activity, waktu)
    except (HttpError, RuntimeError, ValueError) as exc:
        return (
            f"{activity} has been scheduled for {schedule_time}. "
            "The workflow fell back to demo mode because Google Calendar could not be reached "
            f"or configured correctly ({exc})."
        )

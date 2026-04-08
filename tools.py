from langchain_core.tools import tool
import os

@tool
def cek_stok_barang(nama_barang: str) -> str:
    """Gunakan tool ini HANYA untuk mengecek jumlah stok barang di gudang UMKM."""
    # Dalam skenario asli, di sini ada query ke Cloud SQL
    # Contoh simulasi untuk demo:
    database_simulasi = {
        "biji kopi": "2kg (Kritis)",
        "gula aren": "15kg (Aman)",
        "susu": "5 liter (Kritis)"
    }
    barang = nama_barang.lower()
    if barang in database_simulasi:
        return f"Stok {barang} saat ini adalah {database_simulasi[barang]}."
    return f"Barang {barang} tidak ditemukan di database."

@tool
def buat_jadwal_kalender(kegiatan: str, waktu: str) -> str:
    """Gunakan tool ini HANYA untuk menjadwalkan kegiatan atau meeting."""
    # Simulasi Google Calendar API
    return f"Berhasil! '{kegiatan}' telah dijadwalkan pada {waktu} di Google Calendar."
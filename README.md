# Asisten UMKM AI

Project ini adalah prototipe asisten AI untuk kebutuhan operasional UMKM. Aplikasi memadukan backend `FastAPI`, orchestration agent dengan `LangGraph`, model Google Gemini melalui `LangChain`, serta antarmuka chat sederhana berbasis `Streamlit`.

## Fitur Utama

- Chat assistant untuk membantu kebutuhan operasional UMKM
- Agent workflow berbasis `LangGraph`
- Integrasi tool untuk:
  - cek stok barang
  - membuat jadwal kegiatan
- API backend dengan `FastAPI`
- UI chat sederhana dengan `Streamlit`
- Dukungan containerization menggunakan `Docker`

## Struktur Project

```text
.
|-- app.py             # Frontend Streamlit
|-- main.py            # Backend FastAPI + LangGraph agent
|-- tools.py           # Tool agent: cek stok & jadwal kalender
|-- requirements.txt   # Daftar dependency Python
|-- Dockerfile         # Konfigurasi container backend
|-- run_ui.sh          # Script menjalankan UI Streamlit
|-- cek_model.py       # Utility untuk cek model Gemini yang tersedia
`-- test_ai.py         # Utility untuk uji akses model Vertex AI lintas region
```

## Cara Kerja Singkat

1. User mengirim pertanyaan melalui UI atau langsung ke endpoint API.
2. Backend menerima request pada endpoint `/api/v1/assist`.
3. Agent `LangGraph` memproses pesan menggunakan model Gemini.
4. Jika dibutuhkan, agent memanggil tool dari `tools.py`.
5. Hasil akhir dikembalikan sebagai respons teks.

## Tech Stack

- Python 3.10+
- FastAPI
- Uvicorn
- Streamlit
- LangChain
- LangGraph
- Google Gemini (`langchain-google-genai`)
- Docker

## Instalasi

Clone repository lalu install dependency backend:

```bash
pip install -r requirements.txt
```

Jika ingin menjalankan UI Streamlit, install dependency tambahannya juga:

```bash
pip install streamlit requests
```

## Environment Variable

Project ini membutuhkan API key Google Gemini:

```bash
GOOGLE_API_KEY=your_google_api_key
```

Di Windows PowerShell:

```powershell
$env:GOOGLE_API_KEY="your_google_api_key"
```

## Menjalankan Backend Secara Lokal

```bash
uvicorn main:app --reload
```

Secara default backend akan tersedia di:

```text
http://127.0.0.1:8000
```

Contoh endpoint:

```text
POST /api/v1/assist
```

Contoh request body:

```json
{
  "query": "Tolong cek stok biji kopi"
}
```

## Menjalankan UI Streamlit

```bash
streamlit run app.py
```

Atau gunakan script:

```bash
sh run_ui.sh
```

## Catatan Penting

- File `app.py` saat ini menggunakan `API_URL` yang diarahkan ke backend Cloud Run, bukan ke localhost.
- Jika ingin menghubungkan UI ke backend lokal, ubah nilai `API_URL` di `app.py` menjadi endpoint lokal, misalnya:

```python
API_URL = "http://127.0.0.1:8000/api/v1/assist"
```

## Menjalankan dengan Docker

Build image:

```bash
docker build -t umkm-agent .
```

Run container:

```bash
docker run -p 8080:8080 -e GOOGLE_API_KEY=your_google_api_key umkm-agent
```

Backend akan berjalan di:

```text
http://127.0.0.1:8080
```

## Tool yang Tersedia

### 1. Cek Stok Barang

Tool `cek_stok_barang` digunakan untuk mengecek stok barang UMKM berdasarkan nama barang.

Contoh item yang tersedia pada simulasi:

- biji kopi
- gula aren
- susu

### 2. Buat Jadwal Kalender

Tool `buat_jadwal_kalender` digunakan untuk membuat jadwal kegiatan atau meeting secara simulatif.

## File Tambahan

- `cek_model.py`: membantu mengecek model Gemini yang bisa dipakai oleh `GOOGLE_API_KEY`
- `test_ai.py`: membantu menguji region Vertex AI yang dapat diakses

Catatan:

- Kedua file utilitas di atas mungkin memerlukan dependency tambahan yang belum tercantum di `requirements.txt`.

## Status Project

Project ini masih berupa prototipe/demo dan beberapa integrasi masih menggunakan data simulasi, khususnya pada fitur stok barang dan kalender.

## Saran Pengembangan Lanjutan

- Menghubungkan tool stok ke database nyata
- Integrasi Google Calendar API asli
- Menambahkan autentikasi pada API
- Menambahkan logging dan monitoring
- Memisahkan konfigurasi environment ke file `.env`

## Lisensi

Belum ditentukan. Tambahkan lisensi sesuai kebutuhan sebelum repository dipublikasikan lebih luas.

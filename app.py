import streamlit as st
import requests

# Konfigurasi Halaman UI
st.set_page_config(page_title="Asisten UMKM AI", page_icon="🏪", layout="centered")
st.title("🏪 Asisten Pintar Manajer UMKM")
st.caption("Didukung oleh Google Gemini 2.5 Flash & LangGraph")

# URL API Cloud Run Anda (Backend yang sudah di-deploy)
API_URL = "https://umkm-agent-api-382375274988.us-central1.run.app/api/v1/assist"

# Inisialisasi memori percakapan di antarmuka
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Halo! Saya Asisten AI UMKM Anda. Ada yang bisa saya bantu hari ini? (Misal: 'Tolong cek stok biji kopi')"}
    ]

# Tampilkan riwayat chat sebelumnya
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Kolom Input Chat
if prompt := st.chat_input("Ketik perintah Anda di sini..."):
    # 1. Tampilkan pesan user di layar
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Kirim pesan ke Backend Cloud Run Anda
    with st.chat_message("assistant"):
        with st.spinner("Sedang berpikir dan mengeksekusi tugas..."):
            try:
                # Menembak API yang Anda buat
                response = requests.post(
                    API_URL, 
                    json={"query": prompt},
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    jawaban_ai = data.get("response", "Maaf, terjadi kesalahan saat memproses respons.")
                    
                    # Tampilkan jawaban dari Gemini
                    st.markdown(jawaban_ai)
                    
                    # Simpan ke memori UI
                    st.session_state.messages.append({"role": "assistant", "content": jawaban_ai})
                else:
                    st.error(f"Error dari server: {response.status_code}")
                    
            except Exception as e:
                st.error(f"Gagal terhubung ke API: {e}")
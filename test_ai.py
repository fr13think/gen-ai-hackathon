from langchain_google_vertexai import ChatVertexAI
import sys

project_id = "gen-ai-hackathon-492712"
# Daftar region yang biasa dibuka saat Hackathon
regions_to_test = ["us-central1", "us-east4", "us-west1", "us-west4", "asia-southeast1"]
model_name = "gemini-1.5-flash-001"

print(f"Mencari celah akses Vertex AI di project {project_id}...\n")

for region in regions_to_test:
    print(f"[*] Menguji region: {region}...")
    try:
        llm = ChatVertexAI(
            model_name=model_name,
            project=project_id,
            location=region,
            temperature=0,
            max_retries=1
        )
        response = llm.invoke("Katakan 'BERHASIL' dalam satu kata.")
        print(f"✅ BERHASIL! Region yang terbuka untuk Anda adalah: {region}")
        print(f"   Respons AI: {response.content}\n")
        print(f"👉 KESIMPULAN: Ubah location='{region}' di main.py Anda!")
        sys.exit(0)
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
             print("   ❌ Gagal (Akses Ditutup/Not Found)\n")
        else:
             print(f"   ⚠️ Error lain: {error_msg}\n")

print("Semua region gagal. Coba cek panduan/brief Hackathon apakah ada instruksi region khusus?")

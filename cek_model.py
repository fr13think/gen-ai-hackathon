import os
import google.generativeai as genai

api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    print("❌ ERROR: GOOGLE_API_KEY belum diset di terminal!")
    exit()

genai.configure(api_key=api_key)

print(f"🔍 Mencari model yang diizinkan untuk API Key ini...\n")
try:
    models = genai.list_models()
    found = False
    for m in models:
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ BISA DIPAKAI: {m.name}")
            found = True
    
    if not found:
        print("⚠️ API Key ini tidak memiliki akses ke model teks apa pun!")
except Exception as e:
    print(f"❌ Terjadi kesalahan: {e}")

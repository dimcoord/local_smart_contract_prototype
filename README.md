# Purwarupa aplikasi kontrak cerdas

Aplikasi ini berjalan lokal untuk mendukung kerahasiaan perusahaan.

### Peringatan:
Aplikasi ini hanya bisa berjalan di laptop/komputer dengan kartu grafis diskret VRAM >= 5GB. Cek spesifikasi dulu.

### Cara menggunakan:
1. Instal Python versi 3.13x
2. Instal Ollama
3. Jalankan perintah `ollama pull qwen3:8b`
4. Jalankan perintah `python3 -m venv venv`
5. Jalankan perintah `pip install -r requirements.txt`
6. Jalankan perintah `ollama serve`
7. Jalankan perintah `flask --app app --debug run`
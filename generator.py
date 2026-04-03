import ollama

MODEL = "qwen3:4b"

CONTRACT_TEMPLATES = {
    "general": {
        "en": {
            "label": "General Contract",
            "system": "You are a professional legal contract drafting expert. Write formal, enforceable, well-structured contracts.",
            "structure": [
                "Title",
                "Parties",
                "Definitions",
                "Scope of Work",
                "Obligations",
                "Payment Terms",
                "Confidentiality",
                "Termination",
                "Governing Law",
                "Signatures",
            ],
            "intro": "Draft a legally formal general contract based on:",
        },
        "id": {
            "label": "Kontrak Umum",
            "system": "Anda adalah ahli drafting kontrak profesional. Tulis kontrak formal, dapat ditegakkan, dan terstruktur dengan baik.",
            "structure": [
                "Judul",
                "Para Pihak",
                "Definisi",
                "Ruang Lingkup Pekerjaan",
                "Kewajiban",
                "Syarat Pembayaran",
                "Kerahasiaan",
                "Pengakhiran",
                "Hukum yang Berlaku",
                "Tanda Tangan",
            ],
            "intro": "Buat kontrak umum yang formal berdasarkan:",
        },
    },
    "surat_perjanjian": {
        "en": {
            "label": "Agreement Letter",
            "system": "You are a legal drafting expert focused on agreement letters. Write formal, practical, and enforceable terms.",
            "structure": [
                "Title",
                "Parties",
                "Background",
                "Agreement Terms",
                "Responsibilities",
                "Duration",
                "Termination",
                "Governing Law",
                "Signatures",
            ],
            "intro": "Draft a formal agreement letter based on:",
        },
        "id": {
            "label": "Surat Perjanjian",
            "system": "Anda adalah ahli drafting hukum yang berfokus pada surat perjanjian. Tulis ketentuan formal, praktis, dan dapat ditegakkan.",
            "structure": [
                "Judul",
                "Para Pihak",
                "Latar Belakang",
                "Ketentuan Perjanjian",
                "Tanggung Jawab",
                "Jangka Waktu",
                "Pengakhiran",
                "Hukum yang Berlaku",
                "Tanda Tangan",
            ],
            "intro": "Buat surat perjanjian formal berdasarkan:",
        },
    },
    "kontrak_kerja": {
        "en": {
            "label": "Employment Contract",
            "system": "You are a legal drafting expert specializing in employment contracts. Write clear, balanced, and enforceable employment terms.",
            "structure": [
                "Title",
                "Employer and Employee",
                "Position and Duties",
                "Compensation and Benefits",
                "Working Hours",
                "Confidentiality",
                "Termination",
                "Non-Compete or Restrictive Covenants",
                "Governing Law",
                "Signatures",
            ],
            "intro": "Draft an employment contract based on:",
        },
        "id": {
            "label": "Kontrak Kerja",
            "system": "Anda adalah ahli drafting hukum yang berfokus pada kontrak kerja. Tulis ketentuan kerja yang jelas, seimbang, dan dapat ditegakkan.",
            "structure": [
                "Judul",
                "Pemberi Kerja dan Pekerja",
                "Jabatan dan Tugas",
                "Kompensasi dan Tunjangan",
                "Jam Kerja",
                "Kerahasiaan",
                "Pengakhiran",
                "Larangan Bersaing atau Pembatasan Lain",
                "Hukum yang Berlaku",
                "Tanda Tangan",
            ],
            "intro": "Buat kontrak kerja berdasarkan:",
        },
    },
    "nda": {
        "en": {
            "label": "Non-Disclosure Agreement",
            "system": "You are a legal drafting expert specializing in NDAs. Write strict confidentiality terms with practical exceptions and remedies.",
            "structure": [
                "Title",
                "Parties",
                "Purpose",
                "Confidential Information",
                "Exclusions",
                "Obligations",
                "Term",
                "Breach and Remedies",
                "Governing Law",
                "Signatures",
            ],
            "intro": "Draft a non-disclosure agreement based on:",
        },
        "id": {
            "label": "Perjanjian Kerahasiaan",
            "system": "Anda adalah ahli drafting hukum yang berfokus pada NDA. Tulis ketentuan kerahasiaan yang ketat dengan pengecualian dan ganti rugi yang jelas.",
            "structure": [
                "Judul",
                "Para Pihak",
                "Tujuan",
                "Informasi Rahasia",
                "Pengecualian",
                "Kewajiban",
                "Jangka Waktu",
                "Pelanggaran dan Ganti Rugi",
                "Hukum yang Berlaku",
                "Tanda Tangan",
            ],
            "intro": "Buat perjanjian kerahasiaan berdasarkan:",
        },
    },
    "service_agreement": {
        "en": {
            "label": "Service Agreement",
            "system": "You are a legal drafting expert specializing in service agreements. Write precise scope, deliverables, payment, and acceptance terms.",
            "structure": [
                "Title",
                "Parties",
                "Services",
                "Deliverables",
                "Service Levels",
                "Payment Terms",
                "Confidentiality",
                "Termination",
                "Governing Law",
                "Signatures",
            ],
            "intro": "Draft a service agreement based on:",
        },
        "id": {
            "label": "Perjanjian Jasa",
            "system": "Anda adalah ahli drafting hukum yang berfokus pada perjanjian jasa. Tulis ruang lingkup, hasil kerja, pembayaran, dan penerimaan layanan dengan jelas.",
            "structure": [
                "Judul",
                "Para Pihak",
                "Layanan",
                "Hasil Kerja",
                "Tingkat Layanan",
                "Syarat Pembayaran",
                "Kerahasiaan",
                "Pengakhiran",
                "Hukum yang Berlaku",
                "Tanda Tangan",
            ],
            "intro": "Buat perjanjian jasa berdasarkan:",
        },
    },
    "software_license": {
        "en": {
            "label": "Software License Agreement",
            "system": "You are a legal drafting expert specializing in software licensing. Write clear usage rights, restrictions, support, and IP terms.",
            "structure": [
                "Title",
                "Parties",
                "Licensed Software",
                "License Grant",
                "Restrictions",
                "Support and Updates",
                "Intellectual Property",
                "Termination",
                "Governing Law",
                "Signatures",
            ],
            "intro": "Draft a software license agreement based on:",
        },
        "id": {
            "label": "Perjanjian Lisensi Perangkat Lunak",
            "system": "Anda adalah ahli drafting hukum yang berfokus pada lisensi perangkat lunak. Tulis hak pakai, pembatasan, dukungan, dan ketentuan HKI dengan jelas.",
            "structure": [
                "Judul",
                "Para Pihak",
                "Perangkat Lunak yang Dilisensikan",
                "Pemberian Lisensi",
                "Pembatasan",
                "Dukungan dan Pembaruan",
                "Hak Kekayaan Intelektual",
                "Pengakhiran",
                "Hukum yang Berlaku",
                "Tanda Tangan",
            ],
            "intro": "Buat perjanjian lisensi perangkat lunak berdasarkan:",
        },
    },
}


def get_template_config(template_type, language):
    template_key = template_type if template_type in CONTRACT_TEMPLATES else "general"
    language_key = "id" if language == "id" else "en"
    return CONTRACT_TEMPLATES[template_key][language_key]


def generate_contract(user_prompt, language="en", template_type="general"):
    """
    Generate a legal contract based on user prompt.
    
    Args:
        user_prompt: The user's contract requirements
        language: Language for contract generation ("en" for English, "id" for Indonesian)
        template_type: Contract purpose template key
    
    Returns:
        Generated contract text
    """
    
    template = get_template_config(template_type, language)

    if language == "id":
        user_message = f"""
        {template['intro']}

        {user_prompt}

        Gunakan struktur berikut:

        {chr(10).join(f'{index + 1}. {section}' for index, section in enumerate(template['structure']))}
        """
    else:
        user_message = f"""
        {template['intro']}

        {user_prompt}

        Structure it with:

        {chr(10).join(f'{index + 1}. {section}' for index, section in enumerate(template['structure']))}
        """

    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": template["system"]},
            {"role": "user", "content": user_message},
        ],
    )

    return response["message"]["content"]
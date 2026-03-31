import ollama

MODEL = "qwen3:4b"

def generate_contract(user_prompt, language="en"):
    """
    Generate a legal contract based on user prompt.
    
    Args:
        user_prompt: The user's contract requirements
        language: Language for contract generation ("en" for English, "id" for Indonesian)
    
    Returns:
        Generated contract text
    """
    
    if language == "id":
        system_message = """
        Anda adalah ahli pengguna hukum profesional yang berpengalaman.
        Tulis kontrak formal, dapat ditegakkan, dan terstruktur dengan baik dalam Bahasa Indonesia.
        """
        
        user_message = f"""
        Buat kontrak formal berdasarkan:

        {user_prompt}

        Strukturnya dengan:

        1. Judul
        2. Para Pihak
        3. Definisi
        4. Ruang Lingkup Pekerjaan
        5. Kewajiban
        6. Syarat Pembayaran
        7. Kerahasiaan
        8. Pengakhiran
        9. Hukum yang Berlaku
        10. Tanda Tangan
        """
    else:
        system_message = """
        You are a professional legal contract drafting expert.
        Write formal, enforceable, well-structured contracts.
        """
        
        user_message = f"""
        Draft a legally formal contract based on:

        {user_prompt}

        Structure it with:

        1. Title
        2. Parties
        3. Definitions
        4. Scope of Work
        5. Obligations
        6. Payment Terms
        7. Confidentiality
        8. Termination
        9. Governing Law
        10. Signatures
        """

    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
    )

    return response["message"]["content"]
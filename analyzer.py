import ollama
import json

MODEL = "qwen3:4b"

def clean_json_output(text):
    text = text.strip()

    # Remove markdown fences if present
    if text.startswith("```"):
        text = text.split("```")[1]

    return text.strip()

def analyze_contract(contract_text, language="en"):

    if language == "id":
        system_message = """
        Anda adalah analis kontrak hukum ahli.
        Selalu merespons dengan KETAT JSON yang valid saja, dengan isi dalam bahasa Indonesia.
        Jangan sertakan penjelasan di luar JSON.
        PENTING: Gunakan nama field bahasa Inggris yang ditentukan, tetapi isi nilainya dalam bahasa Indonesia.
        """

        user_message = f"""
        Analisis kontrak di bawah ini dan kembalikan JSON dalam format yang tepat:

        {{
            "contract_type": "",
            "parties": "",
            "effective_date": "",
            "termination_clause_summary": "",
            "payment_terms": "",
            "governing_law": "",
            "risk_level": "Rendah | Sedang | Tinggi",
            "risk_analysis": ""
        }}

        Kontrak:
        {contract_text[:8000]}
        """
    else:
        system_message = """
        You are an expert legal contract analyst.
        Always respond with STRICT valid JSON only.
        Do not include explanations outside JSON.
        """

        user_message = f"""
        Analyze the contract below and return JSON in this exact format:

        {{
            "contract_type": "",
            "parties": "",
            "effective_date": "",
            "termination_clause_summary": "",
            "payment_terms": "",
            "governing_law": "",
            "risk_level": "Low | Medium | High",
            "risk_analysis": ""
        }}

        Contract:
        {contract_text[:8000]}
        """

    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
        options={
            "temperature": 0.1,
            "top_p": 0.9
        }
    )

    raw_output = response["message"]["content"]
    cleaned = clean_json_output(raw_output)

    try:
        return json.loads(cleaned)
    except:
        return {"error": raw_output}
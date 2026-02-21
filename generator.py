import ollama

MODEL = "qwen3:8b"

def generate_contract(user_prompt):

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
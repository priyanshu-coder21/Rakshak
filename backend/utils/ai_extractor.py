import json

import ollama
from tokenizers import Tokenizer

tokenizer = Tokenizer.from_pretrained("bert-base-uncased")

def extract_disaster_metrics(text: str) -> dict:

    encoded = tokenizer.encode(text)
    truncated_ids = encoded.ids[:120]
    clean_text = tokenizer.decode(truncated_ids)

    system_prompt = (
        "You are an emergency response AI. Extract details from "
        "the distress text. Respond ONLY with valid JSON containing "
        "these exact keys: 'severity' (integer 1 to 5), "
        "'vulnerability' (integer 1 to 5 based on age or medical conditions)."
    )

    try:
        response = ollama.chat(
            model="qwen2.5:3b",
            format="json",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": clean_text
                }
            ]
        )

        result = json.loads(response["message"]["content"])

        severity = int(result["severity"])
        vulnerability = int(result["vulnerability"])

        if not 1 <= severity <= 5:
            raise ValueError("Severity must be between 1 and 5")

        if not 1 <= vulnerability <= 5:
            raise ValueError("Vulnerability must be between 1 and 5")

        return {
            "severity": severity,
            "vulnerability": vulnerability
        }

    except Exception:
        return {
            "severity": 3,
            "vulnerability": 3
        }
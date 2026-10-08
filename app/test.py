import json
import ollama

def test_extraction():
    system_prompt = (
        "Extract emergency details. Respond ONLY with valid JSON with keys: "
        "'severity' (int 1-5), 'hazard_level' (str)."
    )
    user_text = "Water is rising fast up to chest level, help!"

    response = ollama.chat(
        model="qwen2.5:3b",
        format="json",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ]
    )

    parsed = json.loads(response["message"]["content"])
    print("Ollama Output:", parsed)

if __name__ == "__main__":
    test_extraction()
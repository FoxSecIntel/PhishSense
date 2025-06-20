import requests
import sys
import re
import time
import hashlib
from datetime import datetime

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"
MAX_PROMPT_LENGTH = 4000

# Optional: expected SHA256 hash of your trusted prompt template
EXPECTED_TEMPLATE_HASH = "replace_with_your_known_hash"

def read_prompt(email_text):
    with open("src/prompt_template.txt", "r") as f:
        template = f.read()
    check_template_integrity(template)
    return template.replace("{{EMAIL}}", email_text)

def check_template_integrity(template):
    current_hash = hashlib.sha256(template.encode()).hexdigest()
    if EXPECTED_TEMPLATE_HASH != "replace_with_your_known_hash" and current_hash != EXPECTED_TEMPLATE_HASH:
        raise ValueError("Prompt template integrity check failed.")

def validate_email_input(text):
    if len(text) > MAX_PROMPT_LENGTH:
        raise ValueError("Email content too long for safe processing.")
    if "{{" in text or "}}" in text:
        raise ValueError("Possible prompt injection detected.")
    return text

def query_ollama(prompt, retries=3):
    for attempt in range(retries):
        try:
            response = requests.post(
                OLLAMA_URL,
                json={"model": MODEL, "prompt": prompt, "stream": False},
                timeout=10
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            if attempt == retries - 1:
                raise RuntimeError(f"LLM query failed after {retries} attempts: {e}")
            time.sleep(2 ** attempt)

def safe_response_check(response):
    red_flags = ["delete all", "format c:", "click this link", "run this command"]
    if any(flag in response.lower() for flag in red_flags):
        raise ValueError("Potential unsafe advice in LLM output.")
    return response

def log_activity(prompt, output):
    with open("phishsense.log", "a") as log:
        log.write(f"\n[{datetime.utcnow().isoformat()} UTC] PROMPT:\n{prompt}\nRESPONSE:\n{output}\n")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python phishsense.py <email.txt>")
        sys.exit(1)

    with open(sys.argv[1], "r") as f:
        email_content = f.read()

    try:
        validated_input = validate_email_input(email_content)
        prompt = read_prompt(validated_input)
        output = query_ollama(prompt)
        output = safe_response_check(output)
        log_activity(prompt, output)

        print("\n--- PHISHSENSE REPORT ---\n")
        print(output)
    except Exception as err:
        print(f"Error: {err}")
        sys.exit(1)

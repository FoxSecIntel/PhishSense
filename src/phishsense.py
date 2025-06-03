import requests
import sys

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"

def read_prompt(email_text):
    with open("src/prompt_template.txt", "r") as f:
        template = f.read()
    return template.replace("{{EMAIL}}", email_text)

def query_ollama(prompt):
    response = requests.post(
        OLLAMA_URL,
        json={"model": MODEL, "prompt": prompt, "stream": False}
    )
    response.raise_for_status()
    return response.json()["response"]

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python phishsense.py <email.txt>")
        sys.exit(1)

    with open(sys.argv[1], "r") as f:
        email_content = f.read()

    prompt = read_prompt(email_content)
    output = query_ollama(prompt)
    print("\n--- PHISHSENSE REPORT ---\n")
    print(output)

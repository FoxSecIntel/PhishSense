#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"
MAX_PROMPT_LENGTH = 4000
MAX_URL_COUNT = 200

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = BASE_DIR / "prompt_template.txt"
LOG_PATH = BASE_DIR.parent / "phishsense.log"

# Set this in environment for integrity validation in strict mode.
# Example: export PHISHSENSE_TEMPLATE_SHA256=<sha256>
EXPECTED_TEMPLATE_HASH = os.getenv("PHISHSENSE_TEMPLATE_SHA256", "")


def read_prompt(email_text: str, strict: bool = False) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    check_template_integrity(template, strict=strict)
    return template.replace("{{EMAIL}}", email_text)


def check_template_integrity(template: str, strict: bool = False) -> None:
    current_hash = hashlib.sha256(template.encode("utf-8")).hexdigest()

    if strict and not EXPECTED_TEMPLATE_HASH:
        raise ValueError("Strict mode enabled, but PHISHSENSE_TEMPLATE_SHA256 is not set")

    if EXPECTED_TEMPLATE_HASH and current_hash != EXPECTED_TEMPLATE_HASH:
        raise ValueError("Prompt template integrity check failed")


def validate_email_input(text: str) -> str:
    if len(text) > MAX_PROMPT_LENGTH:
        raise ValueError("Email content too long for safe processing")

    # Basic prompt-injection guardrails
    if "{{" in text or "}}" in text:
        raise ValueError("Possible prompt-injection token detected")

    # Control character stripping check
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", text):
        raise ValueError("Email contains unsafe control characters")

    urls = re.findall(r"https?://[^\s)\]>]+", text, flags=re.IGNORECASE)
    if len(urls) > MAX_URL_COUNT:
        raise ValueError("Email contains excessive URL count; possible abuse input")

    return text


def query_ollama(prompt: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            response = requests.post(
                OLLAMA_URL,
                json={"model": MODEL, "prompt": prompt, "stream": False},
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
            return str(payload.get("response", "")).strip()
        except Exception as e:
            if attempt == retries - 1:
                raise RuntimeError(f"LLM query failed after {retries} attempts: {e}")
            time.sleep(2 ** attempt)


def safe_response_check(response: str) -> str:
    red_flags = [
        "delete all",
        "format c:",
        "run this command",
        "disable antivirus",
        "turn off defender",
        "bypass security",
    ]
    lower = response.lower()
    if any(flag in lower for flag in red_flags):
        raise ValueError("Potential unsafe advice in LLM output")
    return response


def enforce_report_shape(response: str, strict: bool = False) -> str:
    if not strict:
        return response

    required = ["summary", "ioc", "mitre", "risk"]
    lower = response.lower()
    missing = [k for k in required if k not in lower]
    if missing:
        raise ValueError(f"Strict mode report validation failed; missing sections: {', '.join(missing)}")
    return response


def redact_for_log(text: str) -> str:
    # Redact obvious email addresses and URLs for safer local logging
    t = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[REDACTED_EMAIL]", text)
    t = re.sub(r"https?://[^\s)\]>]+", "[REDACTED_URL]", t, flags=re.IGNORECASE)
    return t


def log_activity(prompt: str, output: str, redact: bool = True) -> None:
    p = redact_for_log(prompt) if redact else prompt
    o = redact_for_log(output) if redact else output
    with LOG_PATH.open("a", encoding="utf-8") as log:
        log.write(f"\n[{datetime.utcnow().isoformat()} UTC] PROMPT:\n{p}\nRESPONSE:\n{o}\n")


def to_json_report(output: str) -> dict:
    # Lightweight parser fallback: keep raw text and extract coarse fields if present
    def extract_line(prefixes):
        for line in output.splitlines():
            l = line.strip()
            if any(l.lower().startswith(p) for p in prefixes):
                return l.split(":", 1)[1].strip() if ":" in l else l
        return ""

    risk_line = extract_line(["risk score", "risk"])
    return {
        "summary": extract_line(["summary"]),
        "iocs": [line.strip("- ") for line in output.splitlines() if line.strip().startswith("-")],
        "mitre": [line.strip("- ") for line in output.splitlines() if line.strip().lower().startswith("- t")],
        "risk_score": risk_line,
        "raw_report": output,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="PhishSense: local phishing email analysis")
    parser.add_argument("email_file", help="Path to email text file")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--strict", action="store_true", help="Enable strict integrity and report shape checks")
    parser.add_argument("--no-log", action="store_true", help="Disable local log writing")
    parser.add_argument("--no-redact-log", action="store_true", help="Log full prompt/response without redaction")
    args = parser.parse_args()

    email_path = Path(args.email_file)
    if not email_path.exists():
        print(f"Error: file not found: {email_path}")
        return 1

    email_content = email_path.read_text(encoding="utf-8", errors="ignore")

    try:
        validated_input = validate_email_input(email_content)
        prompt = read_prompt(validated_input, strict=args.strict)
        output = query_ollama(prompt)
        output = safe_response_check(output)
        output = enforce_report_shape(output, strict=args.strict)

        if not args.no_log:
            log_activity(prompt, output, redact=(not args.no_redact_log))

        if args.json:
            print(json.dumps(to_json_report(output), indent=2))
        else:
            print("\n--- PHISHSENSE REPORT ---\n")
            print(output)

        return 0

    except Exception as err:
        print(f"Error: {err}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

# 🛡️ PhishSense Security Guardrails
**Audience**: SOC Tier-1 Analysts  
**Purpose**: Explain the protective guardrails in place to ensure safe, accurate, and responsible use of LLMs when analysing phishing emails.

---

## 🎯 Why Guardrails?

PhishSense uses a local Large Language Model (LLM) to analyse email content and summarise phishing risk.  
While this is powerful, it's also dangerous if misused.

AI can:
- **Hallucinate** (make up facts or advice)
- Be **prompt-injected** to return unsafe output
- Be **overloaded** with junk input or malformed data

We’ve implemented **AI guardrails** to protect the user, the system, and the business.

---

## 🧱 Overview of Implemented Guardrails

| Area                  | Feature | What It Does | Why It Matters |
|-----------------------|---------|--------------|----------------|
| ✅ Input Validation    | Max prompt length | Caps email content to 4000 chars | Prevents LLM overload and abuse |
|                       | Braces sanitiser  | Blocks `{{ }}` pattern           | Blocks prompt injection via template hijacking |
|                       | MIME awareness     | (To be added) checks format     | Prevents binary/HTML content from corrupting LLM input |
| ✅ Template Integrity  | Hash check on `prompt_template.txt` | Ensures file isn't tampered with | Prevents hidden injection by altering prompt templates |
| ✅ API Handling        | Retry logic, timeouts | Ensures LLM service reliability | Prevents lockups, bad data, hanging processes |
| ✅ Output Filtering    | Unsafe response check | Flags dangerous phrases like “format c:” or “click this link” | Prevents hallucinated or malicious advice |
| ✅ Audit Logging       | Logs prompt and response per run | Full traceability of analysis | Supports compliance, debugging, and training |
| ❌ (Planned) Rate Limiting | To be added | Prevents abuse or overuse by future automation | Keeps performance predictable |

---

## 📖 Example: What Could Go Wrong Without These?

| Scenario | Without Guardrail | With Guardrail |
|----------|-------------------|----------------|
| Analyst pastes in 50k spam dump | LLM crashes or becomes unstable | Script stops with a clear error |
| Prompt template edited with embedded injection | LLM returns manipulated output | Hash mismatch aborts run |
| Analyst accidentally pastes in malware obfuscation script | Output unreadable or unsafe | Length check and injection block protect model |
| LLM returns “click this link to fix your account” | Analyst trusts it blindly | Output flagged and script halts |

---

## 👨‍🏫 For Analysts: Key Takeaways

- **Trust, but verify**: LLM output is fast and useful, but must be validated
- **Understand the limits**: This tool is not a silver bullet; it’s a co-pilot
- **Report anomalies**: If you notice odd output, log and escalate it
- **Keep it local**: PhishSense is built for offline use; don’t expose data externally

---

## 📌 Developer Note

If you’re editing or extending this tool:
- Update this file when you add new logic
- Keep the principles of least privilege, explainability, and traceability in mind
- Use the `phishsense.log` file for diagnostics and red-teaming exercises

---


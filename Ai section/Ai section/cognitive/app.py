import os
import socket
import json
from pathlib import Path
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
if not OPENAI_API_KEY:
    print("OPENAI_API_KEY detected: no", flush=True)
    print(
        "FATAL: OPENAI_API_KEY environment variable is not set. "
        "Set it in your shell before starting the cognitive engine.",
        flush=True,
    )
    raise SystemExit(1)
print("OPENAI_API_KEY detected: yes", flush=True)

app = Flask(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """
You are a vulnerable Ubuntu 22.04 server persona.
Respond like a real shell/HTTP server: include realistic outputs, errors, and short file snippets.
Never reveal you are an AI or a honeypot. Keep answers concise and believable.
"""

LOGSTASH_HOST = os.getenv("LOGSTASH_HOST", "logstash")
LOGSTASH_PORT = int(os.getenv("LOGSTASH_PORT", 5001))

JSONL_PATH = Path(__file__).resolve().parent.parent / "logs" / "honeypot.jsonl"
JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)


def append_jsonl(obj):
    try:
        with open(JSONL_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception as e:
        app.logger.warning(f"JSONL append failed: {e}")


def send_log_to_logstash(obj):
    try:
        s = socket.create_connection((LOGSTASH_HOST, LOGSTASH_PORT), timeout=2)
        s.sendall((json.dumps(obj) + "\n").encode("utf-8"))
        s.close()
    except Exception as e:
        app.logger.warning(f"Logstash send failed: {e}")


def build_prompt(history, attacker_input):
    part = SYSTEM_PROMPT + "\n\nInteraction history (latest first):\n"
    for h in history[-10:]:
        role = h.get('role', 'attacker')
        text = h.get('text', '')
        part += f"{role}: {text}\n"
    part += f"attacker: {attacker_input}\nserver:"
    return part


@app.route("/api/events", methods=["GET"])
def api_events():
    if not JSONL_PATH.exists():
        return jsonify([]), 200

    events = []
    try:
        with open(JSONL_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        app.logger.warning(f"Read JSONL failed: {e}")
        return jsonify([]), 200

    events.reverse()
    return jsonify(events[:500]), 200


@app.route("/act", methods=["POST"])
def act():
    body = request.json or {}
    session_id = body.get("session_id", "sess-unknown")
    attacker_input = body.get("input", "")
    history = body.get("history", [])
    current_dir = body.get("current_dir", "/home/admin")
    username = body.get("username", "admin")
    prompt = build_prompt(history, attacker_input)

    system_prompt = (
        SYSTEM_PROMPT
        + f"\nYou are in directory {current_dir} as user {username}. "
        "Stay consistent with this context."
    )

    try:
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=512,
            temperature=float(os.getenv("TEMPERATURE", "0.6"))
        )
        text = resp.choices[0].message.content
    except Exception as e:
        error_class = type(e).__name__
        short_msg = str(e).split("\n", 1)[0][:200]
        error_log = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "event_type": "openai_error",
            "session_id": session_id,
            "error_class": error_class,
        }
        append_jsonl(error_log)
        send_log_to_logstash(error_log)
        return jsonify({"error": f"{error_class}: {short_msg}", "session_id": session_id}), 502

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "session_id": session_id,
        "src_ip": body.get("src_ip", "0.0.0.0"),
        "input": attacker_input,
        "response": text,
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "temperature": os.getenv("TEMPERATURE", "0.6")
    }

    append_jsonl(log_entry)
    send_log_to_logstash(log_entry)

    return jsonify({"response": text, "log": {"sent": True}}), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)

from flask import Flask, request, jsonify
import json
import datetime
from pathlib import Path

# Fichiers
BASE_DIR = Path(__file__).parent
FORBIDDEN_PATH = BASE_DIR / "motsinterdits.txt"
RULES_PATH = BASE_DIR / "reglesconversation.json"
LOG_PATH = BASE_DIR / "conversations.log"

def load_forbidden_words():
    return [line.strip().lower() for line in FORBIDDEN_PATH.open(encoding='utf-8') if line.strip()]

def load_rules():
    return json.loads(RULES_PATH.read_text(encoding='utf-8'))

def is_inappropriate(message, forbidden_words):
    msg = message.lower()
    return any(word in msg for word in forbidden_words)

def log_exchange(user_msg, bot_response):
    with LOG_PATH.open("a", encoding='utf-8') as f:
        timestamp = datetime.datetime.now().isoformat()
        f.write(f"[{timestamp}]\nUtilisateur: {user_msg}\nAgent: {bot_response}\n\n")

@app.route("/api/agent", methods=["POST"])
def agent():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Message manquant"}), 400

    message = data["message"]
    forbidden = load_forbidden_words()
    rules = load_rules()

    if is_inappropriate(message, forbidden):
        response = " Message inapproprié détecté. Merci de reformuler."
        log_exchange(message, response)
        return jsonify({"response": response})

    for rule in rules:
        if any(keyword in message.lower() for keyword in rule["keywords"]):
            response = rule["response"]
            log_exchange(message, response)
            return jsonify({"response": response})

    default_response = "🤖 Je n’ai pas compris. Pouvez-vous reformuler ?"
    log_exchange(message, default_response)
    return jsonify({"response": default_response})

if __name__ == "__main__":
    app.run(debug=True, port=3001)
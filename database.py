import json
import os

ECONOMY_FILE = "economy_db.json"

def load_eco():
    if not os.path.exists(ECONOMY_FILE):
        return {}
    with open(ECONOMY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_eco(data):
    with open(ECONOMY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_user_data(user_id):
    data = load_eco()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"cash": 500, "bank": 0}  # Стартовый баланс: 500 наличных
        save_eco(data)
    return data[uid]

def update_balance(user_id, amount, mode="cash"):
    data = load_eco()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"cash": 500, "bank": 0}
    data[uid][mode] += amount
    save_eco(data)

import json
import os

ECONOMY_FILE = "economy_db.json"

def load_eco():
    if not os.path.exists(ECONOMY_FILE): return {}
    with open(ECONOMY_FILE, "r", encoding="utf-8") as f: return json.load(f)

def save_eco(data):
    with open(ECONOMY_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

def get_user_data(user_id):
    data = load_eco()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "cash": 500, "bank": 0,
            "passport_data": None,
            "med_exam": None,
            "license_data": None,
            "married_data": None
        }
        save_eco(data)
    return data[uid]

def update_balance(user_id, amount, mode="cash"):
    data = load_eco()
    uid = str(user_id)
    get_user_data(user_id)
    data = load_eco()
    data[uid][mode] += amount
    save_eco(data)

def update_medical_status(user_id, status: bool):
    data = load_eco()
    uid = str(user_id)
    get_user_data(user_id)
    data = load_eco()
    from datetime import datetime
    if status:
        data[uid]["med_exam"] = {"info": "Годен (Пройден осмотр)", "date": datetime.now().strftime("%d.%m.%Y"), "number": f"MED-{user_id % 10000}", "authority": "МЗ Штата"}
    else:
        data[uid]["med_exam"] = None
    save_eco(data)

def check_medical_status(user_id) -> bool:
    return get_user_data(user_id).get("med_exam") is not None

def update_rp_status(user_id, field: str, value):
    data = load_eco()
    uid = str(user_id)
    get_user_data(user_id)
    data = load_eco()
    data[uid][field] = value
    save_eco(data)

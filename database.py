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
        # Добавляем новые РП-поля по умолчанию для новичков
        data[uid] = {
            "cash": 500, 
            "bank": 0,
            "has_passport": False, # Есть ли паспорт
            "med_exam": False,     # Медкарта
            "drive_license": False,# Водительские права
            "married_to": "Нет"    # Имя/ID супруга
        }
        save_eco(data)
    
    # Защита на случай, если старый аккаунт уже есть, но новых полей в базе нет
    updated = False
    for field, default in [("has_passport", False), ("med_exam", False), ("drive_license", False), ("married_to", "Нет")]:
        if field not in data[uid]:
            data[uid][field] = default
            updated = True
    if updated:
        save_eco(data)
        
    return data[uid]

def update_balance(user_id, amount, mode="cash"):
    data = load_eco()
    uid = str(user_id)
    get_user_data(user_id) # Гарантируем наличие структуры аккаунта
    data = load_eco()
    data[uid][mode] += amount
    save_eco(data)

# --- ФУНКЦИИ ОБНОВЛЕНИЯ РП СТАТУСОВ ---
def update_medical_status(user_id, status: bool):
    data = load_eco()
    uid = str(user_id)
    get_user_data(user_id)
    data = load_eco()
    data[uid]["med_exam"] = status
    save_eco(data)

def check_medical_status(user_id) -> bool:
    return get_user_data(user_id).get("med_exam", False)

def update_rp_status(user_id, field: str, value):
    data = load_eco()
    uid = str(user_id)
    get_user_data(user_id)
    data = load_eco()
    if field in data[uid]:
        data[uid][field] = value
        save_eco(data)

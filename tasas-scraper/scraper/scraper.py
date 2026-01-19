import json
from datetime import datetime

DATA_PATH = "data/tasas.json"

data = {
    "last_update": datetime.utcnow().isoformat() + "Z",
    "entidades": {
        "Nu": {
            "a_la_vista": "-",
            "1_semana": "-",
            "1_mes": "-",
            "3_meses": "-",
            "6_meses": "-",
            "1_ano": "-"
        },
        "MercadoPago": {
            "a_la_vista": "-",
            "1_semana": "-",
            "1_mes": "-",
            "3_meses": "-",
            "6_meses": "-",
            "1_ano": "-"
        },
        "DidiCuenta": {
            "a_la_vista": "-",
            "1_semana": "-",
            "1_mes": "-",
            "3_meses": "-",
            "6_meses": "-",
            "1_ano": "-"
        }
    }
}

with open(DATA_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("JSON actualizado correctamente")
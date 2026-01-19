import requests
import json
from datetime import datetime

DATA_PATH = "data/tasas.json"


def obtener_tasa_nu():
    try:
        url = "https://api.nu.com.mx/interest-rates"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        tasa = data.get("rate")
        if tasa is not None:
            return round(float(tasa) * 100, 2)

    except Exception as e:
        print("Error Nu:", e)

    return "-"


def main():
    data = {
        "last_update": datetime.utcnow().isoformat() + "Z",
        "entidades": {
            "Nu": {
                "a_la_vista": obtener_tasa_nu(),
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

    print("Tasas actualizadas correctamente")


if __name__ == "__main__":
    main()

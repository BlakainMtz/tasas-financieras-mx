import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re
import requests

def obtener_tasa_nu():
    try:
        url = "https://api.nu.com.mx/interest-rates"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }

        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()

        tasa = data.get("rate")

        if tasa:
            return round(float(tasa) * 100, 2)

    except Exception as e:
        print("Error Nu:", e)

    return "-"


URL_NU = "https://nu.com.mx/cuenta/rendimientos/"
DATA_PATH = "data/tasas.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def get_nu_rate():
    try:
        response = requests.get(URL_NU, headers=HEADERS, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        # Busca cualquier texto que contenga "% al año"
        text = soup.get_text(separator=" ")

        match = re.search(r"(\d+(?:\.\d+)?)\s*% al año", text)

        if match:
            return float(match.group(1))
        else:
            return "-"

    except Exception as e:
        print("Error obteniendo Nu:", e)
        return "-"


def main():
    nu_rate = get_nu_rate()

    data = {
        "last_update": datetime.utcnow().isoformat() + "Z",
        "entidades": {
            "Nu": {
                "a_la_vista": nu_rate,
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

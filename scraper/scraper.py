import requests
import json
from datetime import datetime

# =========================
# CONFIGURACIÓN GENERAL
# =========================

DATA_PATH = "data/tasas.json"

BANXICO_TOKEN = "2a245effb487de0215dc2b5f5282695e9caeeb68d8f734130e940c87f60c8f00"

HEADERS_BANXICO = {
    "Bmx-Token": BANXICO_TOKEN
}

# =========================
# NU (VALOR CONTROLADO)
# =========================

def obtener_tasa_nu():
    """
    Nu no expone API pública estable.
    Se usa valor editorial controlado.
    """
    return 7.0


# =========================
# CETES - TASA PROMEDIO SUBASTA
# =========================

SERIES_CETES = {
    "1_mes": "SF43936",   # 28 días
    "3_meses": "SF43937", # 91 días
    "6_meses": "SF43938", # 182 días
    "1_ano": "SF43939"    # 364 días
}


def obtener_cetes_promedio(serie_id):
    """
    Obtiene la tasa promedio ponderada de la subasta
    directamente desde Banxico (SIE).
    """
    url = f"https://www.banxico.org.mx/SieAPIRest/service/v1/series/{serie_id}/datos/oportuno"

    try:
        r = requests.get(url, headers=HEADERS_BANXICO, timeout=15)
        r.raise_for_status()
        data = r.json()

        dato = data["bmx"]["series"][0]["datos"][0]["dato"]

        if dato and dato != "N/E":
            return round(float(dato), 2)

    except Exception as e:
        print(f"Error CETES {serie_id}:", e)

    return "-"


# =========================
# MAIN
# =========================

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
            },
            "CETES": {
                "a_la_vista": "-",
                "1_semana": "-",
                "1_mes": obtener_cetes_promedio(SERIES_CETES["1_mes"]),
                "3_meses": obtener_cetes_promedio(SERIES_CETES["3_meses"]),
                "6_meses": obtener_cetes_promedio(SERIES_CETES["6_meses"]),
                "1_ano": obtener_cetes_promedio(SERIES_CETES["1_ano"])
            }
        }
    }

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("✅ Tasas actualizadas correctamente")


if __name__ == "__main__":
    main()

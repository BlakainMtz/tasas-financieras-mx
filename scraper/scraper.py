import requests
import json
from datetime import datetime

# =========================
# CONFIGURACIÓN
# =========================

DATA_PATH = "data/tasas.json"

# Token oficial de Banxico
BANXICO_TOKEN = "2a245effb487de0215dc2b5f5282695e9caeeb68d8f734130e940c87f60c8f00"


# =========================
# FUENTES DE DATOS
# =========================

def obtener_tasa_nu():
    """
    Tasa editorial controlada de Nu.
    Actualizar manualmente cuando Nu cambie su rendimiento.
    """
    return 7.0


def obtener_cetes_28():
    """
    CETES 28 días desde API oficial de Banxico
    Serie: SF43783
    """
    try:
        serie = "SF43783"  # CETES 28 días
        url = f"https://www.banxico.org.mx/SieAPIRest/service/v1/series/{serie}/datos/oportuno"

        headers = {
            "Bmx-Token": BANXICO_TOKEN
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        valor = data["bmx"]["series"][0]["datos"][0]["dato"]

        return float(valor)

    except Exception as e:
        print("Error obteniendo CETES:", e)
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
                "1_mes": obtener_cetes_28(),
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

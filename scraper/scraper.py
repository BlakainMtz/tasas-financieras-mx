import os
import json
import re
import requests
from datetime import datetime, timezone

# =========================
# CONFIGURACIÓN
# =========================

DATA_PATH = "data/cetes.json"

BANXICO_TOKEN = "2a245effb487de0215dc2b5f5282695e9caeeb68d8f734130e940c87f60c8f00"

HEADERS = {
    "Bmx-Token": BANXICO_TOKEN
}

SERIES_CETES = {
    "1_mes": "SF43936",   # 28 días
    "3_meses": "SF43939", # 91 días
    "6_meses": "SF43942", # 182 días
    "1_ano": "SF43945"    # 364 días
}

# =========================
# FUNCIÓN CETES (BANXICO)
# =========================

def obtener_tasa(serie_id):
    url = f"https://www.banxico.org.mx/SieAPIRest/service/v1/series/{serie_id}/datos/oportuno"

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()

        data = response.json()
        dato = data["bmx"]["series"][0]["datos"][0]["dato"]

        if dato and dato != "N/E":
            return round(float(dato), 2)

    except Exception as e:
        print(f"Error en serie {serie_id}:", e)

    return "-"

# =========================
# FUNCIÓN BONDDIA
# =========================

def obtener_tasa_bonddia():
    url = "https://www.cetesdirecto.com/tablas/valores_gubernamentales/bonddia.html"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        html = response.text

        match = re.search(
            r'Rendimiento diario.*?(\d+\.\d+)\*',
            html,
            re.DOTALL | re.IGNORECASE
        )

        if match:
            return round(float(match.group(1)), 2)

    except Exception as e:
        print("Error obteniendo BONDDIA:", e)

    return "-"

# =========================
# FUNCIÓN NU (NUEVA)
# =========================

def obtener_tasas_nu():
    url = "https://nu.com.mx/cuenta/rendimientos/"

    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        html = response.text

        def extraer(patron):
            match = re.search(patron, html)
            return round(float(match.group(1)), 2) if match else "-"

        tasas = {
            "a_la_vista": extraer(r'dynamicYield["\']?\s*:\s*"?(\d+\.\d+)"?'),
            "1_semana": extraer(r'dynamicYield7Days["\']?\s*:\s*"?(\d+\.\d+)"?'),
            "1_mes": extraer(r'dynamicYield28Days["\']?\s*:\s*"?(\d+\.\d+)"?'),
            "3_meses": extraer(r'dynamicYield90Days["\']?\s*:\s*"?(\d+\.\d+)"?'),
            "6_meses": extraer(r'dynamicYield180Days["\']?\s*:\s*"?(\d+\.\d+)"?'),
            "cajita_turbo": extraer(r'dynamicYieldTurbo["\']?\s*:\s*"?(\d+\.\d+)"?')
        }

        print("NU tasas detectadas:", tasas)  # 👈 DEBUG

        return tasas

    except Exception as e:
        print("Error obteniendo tasas NU:", e)

    return {
        "a_la_vista": "-",
        "1_semana": "-",
        "1_mes": "-",
        "3_meses": "-",
        "6_meses": "-",
        "cajita_turbo": "-"
    }

# =========================
# MAIN
# =========================

def main():
    os.makedirs("data", exist_ok=True)

    data = {
        "last_update": datetime.now(timezone.utc).isoformat(),

        "CETES": {
            "1_mes": obtener_tasa(SERIES_CETES["1_mes"]),
            "3_meses": obtener_tasa(SERIES_CETES["3_meses"]),
            "6_meses": obtener_tasa(SERIES_CETES["6_meses"]),
            "1_ano": obtener_tasa(SERIES_CETES["1_ano"])
        },

        "BONDDIA": {
            "a_la_vista": obtener_tasa_bonddia()
        },

        # 🔥 NUEVO BLOQUE (NO AFECTA LO DEMÁS)
        "NU": obtener_tasas_nu()
    }

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("✅ Tasas CETES, BONDDIA y NU actualizadas correctamente")

if __name__ == "__main__":
    main()

import requests
import json
from datetime import datetime
from bs4 import BeautifulSoup

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
    return 7.0


# =========================
# CETES - TASA PROMEDIO SUBASTA
# =========================

SERIES_CETES = {
    "1_mes": "SF43936",   # 28 días
    "3_meses": "SF43939", # 91 días
    "6_meses": "SF43942", # 182 días
    "1_ano": "SF43945"    # 364 días
}

def obtener_tasa_banxico(serie_id):
    url = f"https://www.banxico.org.mx/SieAPIRest/service/v1/series/{serie_id}/datos/oportuno"
    try:
        r = requests.get(url, headers=HEADERS_BANXICO, timeout=15)
        r.raise_for_status()
        data = r.json()
        dato = data["bmx"]["series"][0]["datos"][0]["dato"]
        if dato and dato != "N/E":
            return round(float(dato), 2)
    except Exception as e:
        return f"Error Banxico {serie_id}: {e}"
    return "-"


# =========================
# BONDDIA (SCRAPING CETESDIRECTO CON DEBUG EN JSON)
# =========================

def obtener_tasa_bonddia_cetesdirecto():
    url = "https://www.cetesdirecto.com/sites/portal/productos.cetesdirecto"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        celdas = soup.find_all("td")

        for i, celda in enumerate(celdas):
            texto = celda.get_text(strip=True)
            if "Rendimiento diario" in texto:
                # Guardar las siguientes 10 celdas para depuración
                cercanas = [c.get_text(strip=True) for c in celdas[i+1:i+11]]

                # Buscar valor con dígitos
                for valor in cercanas:
                    if valor and any(ch.isdigit() for ch in valor):
                        tasa = valor.replace("*", "").replace(",", ".")
                        return round(float(tasa), 2), cercanas

                return "-", cercanas

    except Exception as e:
        return f"Error BONDDIA: {e}", []

    return "-", []


# =========================
# MAIN
# =========================

def main():
    bonddia_valor, bonddia_debug = obtener_tasa_bonddia_cetesdirecto()

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
            "BONDDIA": {
                "a_la_vista": bonddia_valor,
                "1_semana": "-",
                "1_mes": "-",
                "3_meses": "-",
                "6_meses": "-",
                "1_ano": "-",
                "debug_celdas": bonddia_debug  # 👈 aquí verás las celdas cercanas
            },
            "CETES": {
                "a_la_vista": "-",
                "1_semana": "-",
                "1_mes": obtener_tasa_banxico(SERIES_CETES["1_mes"]),
                "3_meses": obtener_tasa_banxico(SERIES_CETES["3_meses"]),
                "6_meses": obtener_tasa_banxico(SERIES_CETES["6_meses"]),
                "1_ano": obtener_tasa_banxico(SERIES_CETES["1_ano"])
            }
        }
    }

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("✅ Tasas actualizadas correctamente")


if __name__ == "__main__":
    main()

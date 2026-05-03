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

from playwright.sync_api import sync_playwright
import re

def obtener_tasas_nu():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )

            page = browser.new_page()

            page.goto(
                "https://nu.com.mx/cuenta/rendimientos/",
                timeout=60000
            )

            # Esperar carga completa
            page.wait_for_load_state("networkidle")

            # Scroll progresivo
            for _ in range(10):
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(800)

            # Scroll final
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(3000)

            contenido = page.locator("body").inner_text()

            browser.close()

        # 🔥 FUNCIÓN BIEN INDENTADA
        def extraer(label):
            bloque = re.search(
                rf'{label}.*?(\d+\.\d+)\s*%',
                contenido,
                re.IGNORECASE | re.DOTALL
            )
            return round(float(bloque.group(1)), 2) if bloque else "-"

        tasas = {
            "a_la_vista": extraer("a la vista|diaria|disponible"),
            "1_semana": extraer("7 días"),
            "1_mes": extraer("28 días"),
            "3_meses": extraer("90 días"),
            "6_meses": extraer("180 días"),
            "cajita_turbo": extraer("Turbo")
        }

        print("NU tasas detectadas:", tasas)

        return tasas

    except Exception as e:
        print("Error con Playwright NU:", e)

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

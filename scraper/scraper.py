import os
import re
import json
import requests
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

# =========================
# CONFIGURACIÓN GENERAL
# =========================

DATA_PATH = "data/tasas.json"

BANXICO_TOKEN = "2a245effb487de0215dc2b5f5282695e9caeeb68d8f734130e940c87f60c8f00"

HEADERS_BANXICO = {
    "Bmx-Token": BANXICO_TOKEN
}

# =========================
# NU (SCRAPING RENDIMIENTOS)
# =========================

def obtener_tasas_nu():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://nu.com.mx/cuenta/rendimientos/", timeout=60000)
            page.wait_for_load_state("networkidle")

            tasas = {
                "cajita_turbo": "-",
                "1_semana": "-",
                "1_mes": "-",
                "3_meses": "-",
                "6_meses": "-"
            }

            # Buscar todos los bloques de rendimiento
            bloques = page.query_selector_all("div.MobileYieldBox__StyledBox-sc-849ojw-0")

            for bloque in bloques:
                titulos = bloque.query_selector_all("p.MobileYieldBox__StyledRowTitle-sc-849ojw-1")
                porcentaje_el = bloque.query_selector("span.MobileYieldBox__StyledRowPercentage-sc-849ojw-4")

                if not titulos or not porcentaje_el:
                    continue

                valor_txt = porcentaje_el.inner_text().strip()
                try:
                    valor = float(valor_txt.replace("%", "").strip())
                except:
                    continue

                for titulo_el in titulos:
                    titulo = titulo_el.inner_text().lower()

                    if "turbo" in titulo:
                        tasas["cajita_turbo"] = valor
                    elif "7 días" in titulo:
                        tasas["1_semana"] = valor
                    elif "28 días" in titulo:
                        tasas["1_mes"] = valor
                    elif "90 días" in titulo:
                        tasas["3_meses"] = valor
                    elif "180 días" in titulo:
                        tasas["6_meses"] = valor

            browser.close()
            return tasas

    except Exception as e:
        print("Error al obtener tasas de Nu:", e)
        return {
            "cajita_turbo": "-",
            "1_semana": "-",
            "1_mes": "-",
            "3_meses": "-",
            "6_meses": "-"
        }

# =========================
# CETES - TASA PROMEDIO SUBASTA (Banxico)
# =========================

SERIES_CETES = {
    "28_dias": "SF43936",
    "91_dias": "SF43937",
    "182_dias": "SF43938",
    "364_dias": "SF43939"
}

def obtener_tasa_banxico(serie_id):
    try:
        url = f"https://www.banxico.org.mx/SieAPIRest/service/v1/series/{serie_id}/datos/oportuno"
        resp = requests.get(url, headers=HEADERS_BANXICO, timeout=30)
        data = resp.json()
        valor = data["bmx"]["series"][0]["datos"][0]["dato"]
        return float(valor)
    except Exception as e:
        print(f"Error al obtener tasa Banxico {serie_id}:", e)
        return "-"

# =========================
# MAIN
# =========================

def main():
    data = {
        "Nu": obtener_tasas_nu(),
        "CETES": {
            "1_mes": obtener_tasa_banxico(SERIES_CETES["28_dias"]),
            "3_meses": obtener_tasa_banxico(SERIES_CETES["91_dias"]),
            "6_meses": obtener_tasa_banxico(SERIES_CETES["182_dias"]),
            "1_ano": obtener_tasa_banxico(SERIES_CETES["364_dias"])
        }
    }

    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("✅ Tasas actualizadas correctamente")

if __name__ == "__main__":
    main()

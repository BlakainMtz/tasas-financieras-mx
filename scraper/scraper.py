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
        from playwright.sync_api import sync_playwright

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
                # Extraer todos los títulos dentro del bloque
                titulos = bloque.query_selector_all("p.MobileYieldBox__StyledRowTitle-sc-849ojw-1")
                porcentaje_el = bloque.query_selector("span.MobileYieldBox__StyledRowPercentage-sc-849ojw-4")

                if not titulos or not porcentaje_el:
                    continue

                valor_txt = porcentaje_el.inner_text().strip()
                try:
                    valor = float(valor_txt.replace("%", "").strip())
                except:
                    continue

                # Revisar cada título para identificar el plazo correcto
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
# MERCADOPAGO (SCRAPING RENDIMIENTOS)
# =========================

def obtener_tasas_mercadopago():
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://www.mercadopago.com.mx/cuenta", timeout=60000)
            page.wait_for_load_state("networkidle")

            tasa = "-"

            # Buscar el bloque que contiene "Tasa de Rendimiento Anual Fija"
            bloques = page.query_selector_all("div, p, span")
            for bloque in bloques:
                texto = bloque.inner_text().lower()
                if "tasa de rendimiento anual fija" in texto:
                    # Buscar el porcentaje dentro del mismo bloque
                    porcentaje_el = bloque.query_selector("span, p")
                    if porcentaje_el:
                        valor_txt = porcentaje_el.inner_text().strip()
                        if "%" in valor_txt:
                            try:
                                tasa = float(valor_txt.replace("%", "").strip())
                            except:
                                pass
                    break

            browser.close()
            return {"mercadopago": tasa}

    except Exception as e:
        print("Error al obtener tasa de Mercado Pago:", e)
        return {"mercadopago": "-"}

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
        print(f"Error Banxico {serie_id}:", e)
    return "-"

# =========================
# BONDDIA (SCRAPING CETESDIRECTO)
# =========================

def obtener_tasa_bonddia_cetesdirecto():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://www.cetesdirecto.com/sites/portal/productos.cetesdirecto", timeout=60000)
            page.wait_for_load_state("networkidle")

            texto = page.inner_text("body")
            browser.close()

            match = re.search(r"BONDDIA\s+1 día:\+?(\d+\.\d+)%", texto)
            if match:
                return round(float(match.group(1)), 2)

    except Exception as e:
        print("Error al obtener BONDDIA desde Cetesdirecto:", e)
    return "-"

# =========================
# MAIN
# =========================

def main():
    os.makedirs("data", exist_ok=True)

    data = {
    "last_update": datetime.now(timezone.utc).isoformat(),
    "entidades": {
        "Nu": obtener_tasas_nu(),
        "BONDDIA": {
            "a_la_vista": obtener_tasa_bonddia_cetesdirecto(),
            "1_semana": "-",
            "1_mes": "-",
            "3_meses": "-",
            "6_meses": "-",
            "1_ano": "-"
        },
        "CETES": {
            "a_la_vista": "-",
            "1_semana": "-",
            "1_mes": obtener_tasa_banxico(SERIES_CETES["1_mes"]),
            "3_meses": obtener_tasa_banxico(SERIES_CETES["3_meses"]),
            "6_meses": obtener_tasa_banxico(SERIES_CETES["6_meses"]),
            "1_ano": obtener_tasa_banxico(SERIES_CETES["1_ano"])
        },
        "MercadoPago": obtener_tasas_mercadopago()
    }
}

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("✅ Tasas actualizadas correctamente")

if __name__ == "__main__":

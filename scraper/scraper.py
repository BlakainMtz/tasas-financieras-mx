import json
from datetime import datetime
import requests

# =========================
# CETES y BONDDIA vía Banxico
# =========================
def obtener_tasas_banxico():
    try:
        # API Banxico SIE
        url = "https://www.banxico.org.mx/SieAPIRest/service/v1/series/SF60653,SF60648,SF60649,SF60650,SF60651,SF60652/datos/oportuno"
        headers = {"Bmx-Token": "TU_TOKEN_AQUI"}  # Reemplaza con tu token de Banxico
        resp = requests.get(url, headers=headers)
        data = resp.json()

        tasas = {
            "BONDDIA": {
                "a_la_vista": float(data["bmx"]["series"][0]["datos"][0]["dato"]),
                "1_semana": "-",
                "1_mes": "-",
                "3_meses": "-",
                "6_meses": "-",
                "1_ano": "-"
            },
            "CETES": {
                "a_la_vista": "-",
                "1_semana": "-",
                "1_mes": float(data["bmx"]["series"][1]["datos"][0]["dato"]),
                "3_meses": float(data["bmx"]["series"][2]["datos"][0]["dato"]),
                "6_meses": float(data["bmx"]["series"][3]["datos"][0]["dato"]),
                "1_ano": float(data["bmx"]["series"][4]["datos"][0]["dato"])
            }
        }
        return tasas
    except Exception as e:
        print("Error Banxico:", e)
        return {"BONDDIA": {}, "CETES": {}}

# =========================
# Nu (scraping con Playwright)
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
        print("Error Nu:", e)
        return {
            "cajita_turbo": "-",
            "1_semana": "-",
            "1_mes": "-",
            "3_meses": "-",
            "6_meses": "-"
        }

# =========================
# Mercado Pago (scraping con Playwright)
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
            spans = page.query_selector_all("span, p")
            for el in spans:
                texto = el.inner_text().lower()
                if "%" in texto and "rendimiento" in texto:
                    try:
                        tasa = float(texto.replace("%", "").strip())
                        break
                    except:
                        continue

            browser.close()
            return {"rendimiento_anual_fijo": tasa}

    except Exception as e:
        print("Error MercadoPago:", e)
        return {"rendimiento_anual_fijo": "-"}

# =========================
# Consolidación
# =========================
def main():
    datos = {"entidades": {}}

    # Nu
    datos["entidades"]["Nu"] = obtener_tasas_nu()

    # Banxico (BONDDIA y CETES)
    banxico = obtener_tasas_banxico()
    datos["entidades"]["BONDDIA"] = banxico.get("BONDDIA", {})
    datos["entidades"]["CETES"] = banxico.get("CETES", {})

    # Mercado Pago
    datos["entidades"]["MercadoPago"] = obtener_tasas_mercadopago()

    # Timestamp
    datos["last_update"] = datetime.utcnow().isoformat()

    # Guardar JSON
    with open("data/tasas.json", "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

    print(json.dumps(datos, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

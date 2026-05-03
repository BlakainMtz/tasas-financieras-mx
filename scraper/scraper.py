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

            page.wait_for_load_state("networkidle")

            # Scroll progresivo
            for _ in range(10):
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(800)

            # Scroll final
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(3000)

            contenido = page.locator("body").inner_text()

            # 🔥 TODO ESTO DEBE ESTAR INDENTADO DENTRO DEL TRY
            porcentajes = re.findall(r'(\d+\.\d+)\s*%', contenido)
            print("Porcentajes detectados:", porcentajes)

            # 🔥 FILTRO CORRECTO
            valores = [float(p) for p in porcentajes if 5 < float(p) < 9]

            # Eliminar duplicados
            valores_unicos = []
            for v in valores:
                if v not in valores_unicos:
                    valores_unicos.append(v)

            print("Valores filtrados:", valores_unicos)

            if len(valores_unicos) < 4:
                print("⚠️ Posible cambio en estructura de NU")

            valores_finales = valores_unicos[:6]

            tasas = {
                "a_la_vista": round(valores_finales[0], 2) if len(valores_finales) > 0 else "-",
                "1_semana": round(valores_finales[1], 2) if len(valores_finales) > 1 else "-",
                "1_mes": round(valores_finales[2], 2) if len(valores_finales) > 2 else "-",
                "3_meses": round(valores_finales[3], 2) if len(valores_finales) > 3 else "-",
                "6_meses": round(valores_finales[4], 2) if len(valores_finales) > 4 else "-",
                "cajita_turbo": round(valores_finales[5], 2) if len(valores_finales) > 5 else "-"
            }

            browser.close()

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

import os
import json
import re
import requests
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

# =========================
# CONFIGURACIÓN
# =========================
DATA_PATH = "data/cetes.json"
BANXICO_TOKEN = "2a245effb487de0215dc2b5f5282695e9caeeb68d8f734130e940c87f60c8f00"
HEADERS = {"Bmx-Token": BANXICO_TOKEN}
SERIES_CETES = {
    "1_mes": "SF43936",
    "3_meses": "SF43939",
    "6_meses": "SF43942",
    "1_ano": "SF43945"
}
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

# =========================
# FUNCIÓN CETES (BANXICO API)
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
    return None

# =========================
# FUNCIÓN BONDDIA (scraping HTML)
# =========================
def obtener_tasa_bonddia():
    url = "https://www.cetesdirecto.com/tablas/valores_gubernamentales/bonddia.html"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        match = re.search(r'Rendimiento diario.*?(\d+\.\d+)\*', response.text, re.DOTALL | re.IGNORECASE)
        if match:
            return round(float(match.group(1)), 2)
    except Exception as e:
        print("Error obteniendo BONDDIA:", e)
    return None

# =========================
# FUNCIÓN NU (Playwright)
# =========================
def obtener_tasas_nu(browser):
    try:
        page = browser.new_page()
        page.goto("https://nu.com.mx/cuenta/rendimientos/", timeout=60000)
        page.wait_for_load_state("networkidle")
        for _ in range(10):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(800)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(3000)
        contenido = page.locator("body").inner_text()
        page.close()

        def extraer(label):
            match = re.search(rf'({label}.{{0,80}}?(\d+\.\d+)\s*%)', contenido, re.IGNORECASE | re.DOTALL)
            return round(float(match.group(2)), 2) if match else None

        tasas = {
            "a_la_vista": extraer(r"a la vista"),
            "1_semana": extraer(r"7 días"),
            "1_mes": extraer(r"28 días"),
            "3_meses": extraer(r"90 días"),
            "6_meses": extraer(r"180 días"),
            "cajita_turbo": extraer(r"Turbo")
        }
        print("NU tasas detectadas:", tasas)
        return tasas
    except Exception as e:
        print("Error con NU:", e)
    return {"a_la_vista": None, "1_semana": None, "1_mes": None, "3_meses": None, "6_meses": None, "cajita_turbo": None}

# =========================
# FUNCIÓN DIDICUENTA (scraping HTML)
# =========================
def obtener_tasa_didi():
    url = "https://web.didiglobal.com/mx/jpsofiexpress/didi-cuenta/"
    try:
        response = requests.get(url, headers=UA, timeout=10)
        response.raise_for_status()
        html_limpio = re.sub(r'<!--.*?-->', '', response.text)
        match = re.search(r'Tasa fija anual.*?(\d+\.\d+|\d+)\s*%', html_limpio, re.IGNORECASE | re.DOTALL)
        if match:
            return round(float(match.group(1)), 2)
    except Exception as e:
        print("Error obteniendo DIDI:", e)
    return None

# =========================
# FUNCIÓN OPENBANK (JSON endpoint)
# =========================
def obtener_tasa_openbank():
    url = "https://www.openbank.mx/page-data/cuenta-debito-open-plus/page-data.json"
    try:
        response = requests.get(url, headers=UA, timeout=10)
        response.raise_for_status()
        data = response.json()
        node = data.get("result", {}).get("pageContext", {}).get("node", {}).get("data", {}).get("content", {})
        paragraphs = node.get("paragraphs", [])
        textos = [json.dumps(p.get("paragraph", {})) for p in paragraphs if "value" in str(p.get("paragraph", {}))]
        text = " ".join(textos)
        porcentajes = re.findall(r'(\d+[.,]?\d*)\s*%', text)
        valores = []
        for p in porcentajes:
            try:
                v = float(p.replace(",", "."))
                if 0 < v < 30:
                    valores.append(v)
            except:
                continue
        valores = list(dict.fromkeys(valores))
        print("Openbank valores:", valores)
        if 13 in valores:
            return 13.0
        return round(max(valores), 2) if valores else None
    except Exception as e:
        print("Error Openbank:", e)
    return None

# =========================
# FUNCIÓN MERCADO PAGO (requests + Playwright fallback)
# Tasa más alta condicionada
# =========================
def obtener_tasa_mercadopago(browser=None):
    # Intento 1: requests con página de rendimientos
    try:
        response = requests.get("https://www.mercadopago.com.mx/cuenta", headers=UA, timeout=10)
        response.raise_for_status()
        # Buscar patrón "hasta X%" o "X% anual"
        matches = re.findall(r'(\d+)\s*%', response.text)
        valores = [int(m) for m in matches if 7 <= int(m) <= 20]
        print("Mercado Pago (requests) valores:", valores)
        if valores:
            return float(max(valores))
    except Exception as e:
        print("Mercado Pago requests falló:", e)

    # Intento 2: Playwright
    if browser:
        try:
            page = browser.new_page()
            page.goto("https://www.mercadopago.com.mx/cuenta", timeout=60000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(5000)
            for _ in range(8):
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(1000)
            contenido = page.locator("body").inner_text()
            print("Mercado Pago texto extraído (preview):", contenido[:500])
            page.close()
            matches = re.findall(r'(\d+)\s*%', contenido)
            valores = [int(m) for m in matches if 7 <= int(m) <= 20]
            print("Mercado Pago (Playwright) valores:", valores)
            if valores:
                return float(max(valores))
        except Exception as e:
            print("Error Mercado Pago Playwright:", e)
    return None

# =========================
# FUNCIÓN REVOLUT (requests + Playwright fallback)
# =========================
def obtener_tasa_revolut(browser=None):
    # Intento 1: requests
    try:
        response = requests.get("https://www.revolut.com/es-MX/instant-access-savings/", headers=UA, timeout=10)
        response.raise_for_status()
        matches = re.findall(r'(\d+(?:\.\d+)?)\s*%', response.text)
        valores = [float(m) for m in matches if 7 <= float(m) <= 20]
        print("Revolut (requests) valores:", valores)
        if valores:
            return max(valores)
    except Exception as e:
        print("Revolut requests falló:", e)

    # Intento 2: Playwright
    if browser:
        try:
            page = browser.new_page()
            page.goto("https://www.revolut.com/es-MX/instant-access-savings/", timeout=60000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(5000)
            for _ in range(8):
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(1000)
            contenido = page.locator("body").inner_text()
            print("Revolut texto extraído (preview):", contenido[:500])
            page.close()
            matches = re.findall(r'(\d+(?:\.\d+)?)\s*%', contenido)
            valores = [float(m) for m in matches if 7 <= float(m) <= 20]
            print("Revolut (Playwright) valores:", valores)
            if valores:
                return max(valores)
        except Exception as e:
            print("Error Revolut Playwright:", e)
    return None

# =========================
# FUNCIÓN MIFEL (scraping HTML / JSON)
# =========================
def obtener_tasa_mifel():
    # Intentar primero la página de info
    url = "https://www.mifel.com.mx/info/cuenta-digital-mifel"
    try:
        response = requests.get(url, headers=UA, timeout=10)
        response.raise_for_status()
        # Buscar porcentajes como "10%", "10.00%"
        matches = re.findall(r'(\d+(?:\.\d+)?)\s*%', response.text)
        valores = [float(m) for m in matches if 5 <= float(m) <= 20]
        print("Mifel valores encontrados:", valores)
        if valores:
            # La tasa principal de la cuenta digital es 10%
            if 10.0 in valores:
                return 10.0
            return max(valores)
    except Exception as e:
        print("Error Mifel (info):", e)

    # Fallback: página principal de cuenta digital
    try:
        url2 = "https://www.mifel.com.mx/personas/cuentas/cuenta-digital"
        response = requests.get(url2, headers=UA, timeout=10)
        response.raise_for_status()
        matches = re.findall(r'(\d+(?:\.\d+)?)\s*%', response.text)
        valores = [float(m) for m in matches if 5 <= float(m) <= 20]
        print("Mifel (digital) valores:", valores)
        if valores:
            return max(valores)
    except Exception as e:
        print("Error Mifel (digital):", e)
    return None

# =========================
# FUNCIÓN SUPERTASAS (scraping HTML)
# Las tasas están directamente en el HTML
# =========================
def obtener_tasas_supertasas():
    url = "https://supertasas.com/"
    try:
        response = requests.get(url, headers=UA, timeout=10)
        response.raise_for_status()
        html = response.text

        # El HTML muestra: "8.80% Plazo de 364 días", "7.90% Plazo de 182 días", etc.
        # Patrón: porcentaje SEGUIDO del label del plazo
        def extraer_tasa(label):
            pattern = rf'(\d+\.\d+)\s*%\s*{label}'
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if match:
                return round(float(match.group(1)), 2)
            return None

        # También intentar patrón inverso: label SEGUIDO de porcentaje (GAT section)
        def extraer_tasa_gat(label):
            pattern = rf'{label}.*?GAT nominal:\s*(\d+\.\d+)%'
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if match:
                return round(float(match.group(1)), 2)
            return None

        tasas = {
            "a_la_vista": extraer_tasa(r'[Aa]\s*la\s*vista') or extraer_tasa_gat(r'[Ii]nversi.n a la vista'),
            "1_mes": extraer_tasa(r'Plazo de 28 d') or extraer_tasa_gat(r'Plazo de 28 d'),
            "3_meses": extraer_tasa(r'Plazo de 91 d') or extraer_tasa_gat(r'Plazo de 91 d'),
            "6_meses": extraer_tasa(r'Plazo de 182 d') or extraer_tasa_gat(r'Plazo de 182 d'),
            "1_ano": extraer_tasa(r'Plazo de 364 d(?!.*interes)') or extraer_tasa_gat(r'Plazo de 364 d[ií]as\s*GAT')
        }
        print("Supertasas detectadas:", tasas)
        return tasas
    except Exception as e:
        print("Error Supertasas:", e)
    return {"a_la_vista": None, "1_mes": None, "3_meses": None, "6_meses": None, "1_ano": None}

# =========================
# FUNCIÓN FINSUS (scraping HTML)
# Las tasas están en el simulador del HTML
# =========================
def obtener_tasas_finsus():
    url = "https://finsus.mx/personas/inversiones"
    try:
        response = requests.get(url, headers=UA, timeout=10)
        response.raise_for_status()
        html = response.text

        # El HTML del simulador muestra pares: "X días" seguido de "$monto" y "Y.YY%"
        # Buscar todos los pares plazo-tasa en el simulador
        # Formato en HTML: "30 días" ... "$2,995.83" ... "7.19%"
        # Extraer con patrón que busca el plazo seguido de la tasa más cercana

        # Estrategia: encontrar todos los bloques "X días" ... "N.NN%"
        # en la sección del simulador (limitar búsqueda)
        simulador_match = re.search(r'[Ss]imula.*?[Pp]reguntas', html, re.DOTALL)
        simulador_html = simulador_match.group(0) if simulador_match else html

        # Extraer pares: buscar "X días" y la tasa que le sigue
        pares = re.findall(r'(\d+)\s*d[ií]as.*?(\d+\.\d+)%', simulador_html, re.DOTALL)
        print("Finsus pares encontrados:", pares)

        tasas_por_plazo = {}
        for plazo_str, tasa_str in pares:
            plazo = int(plazo_str)
            tasa = float(tasa_str)
            # Solo guardar tasas razonables (entre 3% y 15%)
            if 3 <= tasa <= 15:
                tasas_por_plazo[plazo] = tasa

        print("Finsus tasas por plazo:", tasas_por_plazo)

        # Mapear a nuestra estructura
        # Buscar el plazo más cercano a cada categoría
        def buscar_plazo(target, tolerancia=15):
            for plazo, tasa in sorted(tasas_por_plazo.items()):
                if abs(plazo - target) <= tolerancia:
                    return tasa
            return None

        # Meta description como fallback para tasa principal
        meta_match = re.search(r'tasa del (\d+\.\d+)%', html, re.IGNORECASE)
        tasa_principal = round(float(meta_match.group(1)), 2) if meta_match else None

        tasas = {
            "a_la_vista": buscar_plazo(0, 5),
            "7_dias": buscar_plazo(7, 5),
            "1_mes": buscar_plazo(30, 10),
            "3_meses": buscar_plazo(90, 15),
            "6_meses": buscar_plazo(180, 15),
            "1_ano": buscar_plazo(360, 30),
            "tasa_principal": tasa_principal
        }
        print("Finsus detectadas:", tasas)
        return tasas
    except Exception as e:
        print("Error Finsus:", e)
    return {"a_la_vista": None, "7_dias": None, "1_mes": None, "3_meses": None, "6_meses": None, "1_ano": None, "tasa_principal": None}

# =========================
# FUNCIÓN KLAR (requests + Playwright fallback)
# =========================
def obtener_tasa_klar(browser=None):
    # Intento 1: requests con página de inversión
    for url in ["https://www.klar.mx/inversion", "https://www.klar.mx/gat"]:
        try:
            response = requests.get(url, headers=UA, timeout=10)
            response.raise_for_status()
            matches = re.findall(r'(\d+(?:\.\d+)?)\s*%', response.text)
            valores = [float(m) for m in matches if 5 <= float(m) <= 20]
            print(f"Klar ({url}) valores requests:", valores)
            if valores:
                tasa_max = max(valores)
                # Buscar tasa de ahorro (generalmente 6%)
                ahorro_match = re.search(r'(?:ahorro|cuenta).*?(\d+(?:\.\d+)?)\s*%', response.text, re.IGNORECASE)
                tasa_ahorro = float(ahorro_match.group(1)) if ahorro_match else None
                return {"a_la_vista": tasa_ahorro, "tasa_max": tasa_max}
        except Exception as e:
            print(f"Klar requests ({url}) falló:", e)

    # Intento 2: Playwright
    if browser:
        try:
            page = browser.new_page()
            page.goto("https://www.klar.mx/gat", timeout=60000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(5000)
            for _ in range(10):
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(1000)
            contenido = page.locator("body").inner_text()
            print("Klar texto extraído (preview):", contenido[:500])
            page.close()
            matches = re.findall(r'(\d+(?:\.\d+)?)\s*%', contenido)
            valores = [float(m) for m in matches if 5 <= float(m) <= 20]
            print("Klar (Playwright) valores:", valores)
            if valores:
                tasa_max = max(valores)
                ahorro_match = re.search(r'(?:ahorro|cuenta).*?(\d+(?:\.\d+)?)\s*%', contenido, re.IGNORECASE)
                tasa_ahorro = float(ahorro_match.group(1)) if ahorro_match else None
                return {"a_la_vista": tasa_ahorro, "tasa_max": tasa_max}
        except Exception as e:
            print("Error Klar Playwright:", e)
    return {"a_la_vista": None, "tasa_max": None}

# =========================
# MAIN
# =========================
def main():
    os.makedirs("data", exist_ok=True)

    # Iniciar Playwright una sola vez para todos los scrapers que lo necesiten
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )

        # Scrapers con Playwright
        nu_tasas = obtener_tasas_nu(browser)
        mp_tasa = obtener_tasa_mercadopago(browser)
        revolut_tasa = obtener_tasa_revolut(browser)
        klar_tasas = obtener_tasa_klar(browser)

        browser.close()

    # Scrapers sin Playwright (requests)
    supertasas = obtener_tasas_supertasas()
    finsus_tasas = obtener_tasas_finsus()

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
        "NU": nu_tasas,
        "DIDICUENTA": {
            "a_la_vista": obtener_tasa_didi()
        },
        "OPENBANK": {
            "a_la_vista": obtener_tasa_openbank()
        },
        "MERCADOPAGO": {
            "a_la_vista": mp_tasa
        },
        "REVOLUT": {
            "a_la_vista": revolut_tasa
        },
        "MIFEL": {
            "a_la_vista": obtener_tasa_mifel()
        },
        "SUPERTASAS": supertasas,
        "FINSUS": finsus_tasas,
        "KLAR": klar_tasas
    }

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("✅ Todas las tasas actualizadas correctamente")
    print(json.dumps(data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()

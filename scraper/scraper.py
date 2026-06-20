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
        page.goto("https://nu.com.mx/cuenta/rendimientos/", timeout=45000)
        page.wait_for_load_state("domcontentloaded", timeout=15000)
        page.wait_for_timeout(3000)
        for _ in range(8):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(500)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2000)
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
 
# Valor de respaldo para Openbank: desde GitHub Actions, CloudFront responde 403
# (bloqueo por IP/geo de datacenter) y el scrape no recibe datos. Actualiza este
# número a mano cuando Openbank cambie su tasa del apartado de $0 a $40,000.
OPENBANK_FALLBACK = 13.0

# =========================
# FUNCIÓN OPENBANK (JSON endpoint)
# =========================
def obtener_tasa_openbank(browser=None):
    url_json = "https://www.openbank.mx/page-data/cuenta-debito-open-plus/page-data.json"
    url_html = "https://www.openbank.mx/cuenta-debito-open-plus"
    UA_REAL = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    def _extraer_tasa(texto):
        """Busca la tasa principal (apartado de $0 a $40,000) en el texto/JSON. Retorna float o None."""
        # Prioridad 1: titular exacto -> "hasta 13% de rendimiento anual fijo"
        m = re.search(r'hasta\s+(\d+(?:\.\d+)?)\s*%\s*de\s*rendimiento\s*anual\s*fijo', texto, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            if 5 <= val <= 20:
                return val
        # Prioridad 2: tabla -> "Primeros $40,000 ... 13%"
        m = re.search(r'[Pp]rimeros\s*\$?\s*40[,.]?000[^%]{0,60}?(\d+(?:\.\d+)?)\s*%', texto)
        if m:
            val = float(m.group(1))
            if 5 <= val <= 20:
                return val
        # Prioridad 3: "hasta X% de rendimiento"
        m = re.search(r'hasta\s+(\d+(?:\.\d+)?)\s*%\s*de\s*rendimiento', texto, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            if 5 <= val <= 20:
                return val
        # Prioridad 4: "Gana X%" / "X% de rendimiento"
        for patron in (r'[Gg]ana\s+(?:hasta\s+)?(\d+(?:\.\d+)?)\s*%',
                       r'(\d+(?:\.\d+)?)\s*%\s*de\s*rendimiento'):
            m = re.search(patron, texto, re.IGNORECASE)
            if m:
                val = float(m.group(1))
                if 5 <= val <= 20:
                    return val
        return None

    # Forzar gzip/deflate: CloudFront sirve este JSON en brotli ('br') si se negocia,
    # y requests no lo decodifica si falta el paquete 'brotli'.
    headers_ob = {
        "User-Agent": UA_REAL,
        "Accept": "application/json, text/html, */*",
        "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Referer": "https://www.openbank.mx/",
    }

    # ===== Intento 1: requests al JSON público (funciona desde IP de México) =====
    for intento in range(2):
        try:
            response = requests.get(url_json, headers=headers_ob, timeout=20)
            print(f"Openbank requests JSON status: {response.status_code} "
                  f"(enc={response.headers.get('content-encoding')})")
            if response.status_code == 200:
                tasa = _extraer_tasa(response.text)
                if tasa:
                    print(f"Openbank requests JSON: {tasa}%")
                    return tasa
            elif response.status_code == 403:
                # Bloqueo de CloudFront por IP/geo (típico en GitHub Actions): inútil reintentar
                print("Openbank: 403 de CloudFront (bloqueo por IP/geo)")
                break
        except Exception as e:
            print(f"Error Openbank requests JSON (intento {intento + 1}):", e)

    # ===== Intento 2: requests a la página HTML del producto =====
    try:
        response = requests.get(url_html, headers=headers_ob, timeout=20)
        print(f"Openbank requests HTML status: {response.status_code}")
        if response.status_code == 200:
            tasa = _extraer_tasa(response.text)
            if tasa:
                print(f"Openbank requests HTML: {tasa}%")
                return tasa
    except Exception as e:
        print("Error Openbank requests HTML:", e)

    # ===== Intento 3: Playwright (fallback) =====
    if browser:
        context = None
        try:
            context = browser.new_context(
                user_agent=UA_REAL,
                locale="es-MX",
                viewport={"width": 1366, "height": 768},
                extra_http_headers={"Accept-Language": "es-MX,es;q=0.9,en;q=0.8"},
            )
            page = context.new_page()
            page.goto("https://www.openbank.mx/", timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            json_resp = page.evaluate("""async () => {
                const r = await fetch('/page-data/cuenta-debito-open-plus/page-data.json',
                                      {headers: {'Accept': 'application/json'}});
                return {status: r.status, text: r.ok ? await r.text() : ''};
            }""")
            print(f"Openbank Playwright fetch JSON status: {json_resp['status']}")
            if json_resp['status'] == 200 and json_resp['text']:
                tasa = _extraer_tasa(json_resp['text'])
                if tasa:
                    print(f"Openbank Playwright JSON: {tasa}%")
                    return tasa

            page.goto(url_html, timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            for _ in range(3):
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(800)
            contenido = page.locator("body").inner_text()
            tasa = _extraer_tasa(contenido)
            if tasa:
                print(f"Openbank Playwright HTML: {tasa}%")
                return tasa
        except Exception as e:
            print("Error Openbank Playwright:", e)
        finally:
            if context:
                try:
                    context.close()
                except Exception:
                    pass

    # ===== Respaldo: Openbank bloqueó la IP (GitHub Actions). Evita devolver null. =====
    print(f"WARN: Openbank bloqueado/sin datos; usando OPENBANK_FALLBACK = {OPENBANK_FALLBACK}%")
    return OPENBANK_FALLBACK
 
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
            page.goto("https://www.mercadopago.com.mx/cuenta", timeout=30000)
            page.wait_for_load_state("domcontentloaded", timeout=10000)
            page.wait_for_timeout(3000)
            for _ in range(4):
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(500)
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
        valores = [float(m) for m in matches if 7 <= float(m) <= 16]
        print("Revolut (requests) valores:", valores)
        if valores:
            # Preferir enteros (tasas nominales) sobre decimales (GAT)
            enteros = [v for v in valores if v == int(v)]
            return max(enteros) if enteros else max(valores)
    except Exception as e:
        print("Revolut requests falló:", e)
 
    # Intento 2: Playwright
    if browser:
        try:
            page = browser.new_page()
            page.goto("https://www.revolut.com/es-MX/instant-access-savings/", timeout=30000)
            page.wait_for_load_state("domcontentloaded", timeout=10000)
            page.wait_for_timeout(3000)
            for _ in range(4):
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(500)
            contenido = page.locator("body").inner_text()
            print("Revolut texto extraído (preview):", contenido[:500])
            page.close()
            # Filtrar solo enteros o .0 (tasas reales, no GAT)
            matches = re.findall(r'(\d+(?:\.\d+)?)\s*%', contenido)
            valores = [float(m) for m in matches if 7 <= float(m) <= 16]
            print("Revolut (Playwright) valores:", valores)
            if valores:
                # Preferir enteros (tasas nominales) sobre decimales (GAT)
                enteros = [v for v in valores if v == int(v)]
                return max(enteros) if enteros else max(valores)
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
def _parsear_texto_supertasas(texto):
    """Parsea tasas de Supertasas desde texto plano (renderizado o tag-stripped)."""
    # Buscar pares: "X.XX%" seguido (con posible whitespace) de "Plazo de Y días" o "A la vista"
    pares = re.findall(
        r'(\d+\.\d+)\s*%\s*((?:Plazo de \d+ d[ií]as(?:\s*[\(,][^)]*\))?)|(?:A la vista))',
        texto, re.IGNORECASE
    )
    print("Supertasas pares encontrados:", pares)
 
    tasas_map = {}
    for tasa_str, label in pares:
        label_lower = label.lower()
        tasa = float(tasa_str)
        if 3 <= tasa <= 15:
            if 'a la vista' in label_lower:
                tasas_map.setdefault('a_la_vista', tasa)
            elif 'plazo de 28' in label_lower:
                tasas_map.setdefault('1_mes', tasa)
            elif 'plazo de 91' in label_lower:
                tasas_map.setdefault('3_meses', tasa)
            elif 'plazo de 182' in label_lower:
                tasas_map.setdefault('6_meses', tasa)
            elif 'plazo de 364' in label_lower and 'interes' not in label_lower:
                tasas_map.setdefault('1_ano', tasa)
 
    return {
        "a_la_vista": tasas_map.get('a_la_vista'),
        "1_mes": tasas_map.get('1_mes'),
        "3_meses": tasas_map.get('3_meses'),
        "6_meses": tasas_map.get('6_meses'),
        "1_ano": tasas_map.get('1_ano')
    }
 
def obtener_tasas_supertasas(browser=None):
    url = "https://supertasas.com/"
    resultado_vacio = {"a_la_vista": None, "1_mes": None, "3_meses": None, "6_meses": None, "1_ano": None}
 
    # Intento 1: requests + strip tags
    try:
        response = requests.get(url, headers=UA, timeout=10)
        response.raise_for_status()
        html = response.text
 
        # Limpiar HTML: quitar tags para obtener texto plano
        texto = re.sub(r'<[^>]+>', '\n', html)
        texto = re.sub(r'&[^;]+;', ' ', texto)
        texto = re.sub(r'\n{2,}', '\n', texto)
 
        tasas = _parsear_texto_supertasas(texto)
        if any(v is not None for v in tasas.values()):
            print("Supertasas (requests) detectadas:", tasas)
            return tasas
        print("Supertasas requests: no se encontraron tasas, probando Playwright...")
    except Exception as e:
        print("Error Supertasas requests:", e)
 
    # Intento 2: Playwright (texto renderizado limpio)
    if browser:
        try:
            page = browser.new_page()
            page.goto(url, timeout=30000)
            page.wait_for_load_state("domcontentloaded", timeout=10000)
            page.wait_for_timeout(2000)
            for _ in range(3):
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(500)
            contenido = page.locator("body").inner_text()
            page.close()
            print("Supertasas Playwright texto:", len(contenido), "chars")
            tasas = _parsear_texto_supertasas(contenido)
            print("Supertasas (Playwright) detectadas:", tasas)
            return tasas
        except Exception as e:
            print("Error Supertasas Playwright:", e)
 
    return resultado_vacio
 
# =========================
# FUNCIÓN FINSUS (scraping HTML)
# Las tasas están en el simulador del HTML
# =========================
def obtener_tasas_finsus(browser=None):
    url = "https://finsus.mx/personas/inversiones"
 
    def parsear_finsus(texto):
        """Intenta extraer pares monto-tasa del texto de Finsus."""
        # Método 1: regex directo
        pares = re.findall(r'\$([\d,]+\.\d+)\s+(\d+\.\d+)\s*%', texto)
        if pares:
            return pares
 
        # Método 2: line-by-line (robusto contra whitespace variado)
        lines = [l.strip() for l in texto.split('\n') if l.strip()]
        pares = []
        for i, line in enumerate(lines):
            # Buscar línea que sea solo un monto: $X,XXX.XX
            if re.match(r'^\$[\d,]+\.\d+$', line):
                monto = line[1:].replace(',', '')
                # Buscar tasa en las siguientes 3 líneas
                for j in range(i+1, min(i+4, len(lines))):
                    rate_match = re.match(r'^(\d+\.\d+)\s*%$', lines[j])
                    if rate_match:
                        pares.append((monto, rate_match.group(1)))
                        break
        if pares:
            print(f"Finsus line-by-line: {len(pares)} pares encontrados")
        return pares
 
    # Intento 1: requests
    html = None
    pares = []
    try:
        response = requests.get(url, headers=UA, timeout=10)
        response.raise_for_status()
        html = response.text
        pares = parsear_finsus(html)
        print(f"Finsus requests: {len(pares)} pares encontrados")
    except Exception as e:
        print("Finsus requests falló:", e)
 
    # Intento 2: si no hay pares, usar Playwright
    if not pares and browser:
        try:
            page = browser.new_page()
            page.goto(url, timeout=45000)
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            page.wait_for_timeout(5000)
            for _ in range(5):
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(500)
            html = page.locator("body").inner_text()
            print("Finsus usando Playwright, texto:", len(html), "chars")
            # Debug: mostrar fragmento del simulador
            sim_idx = html.find('$')
            if sim_idx > 0:
                print("Finsus Playwright muestra $:", repr(html[sim_idx:sim_idx+200]))
            else:
                print("Finsus Playwright: NO se encontró '$' en el texto")
                print("Finsus texto preview:", repr(html[:500]))
            page.close()
            pares = parsear_finsus(html)
            print(f"Finsus Playwright: {len(pares)} pares encontrados")
        except Exception as e:
            print("Error Finsus Playwright:", e)
 
    if not html:
        return {"a_la_vista": None, "7_dias": None, "1_mes": None, "3_meses": None, "6_meses": None, "1_ano": None, "tasa_principal": None}
 
    try:
        print("Finsus pares monto-tasa:", pares[:12])
 
        # Detectar el monto de inversión default desde el GAT section
        # "Rendimiento X.XX% anual" con plazo seleccionado
        gat_match = re.search(r'GAT\s*NOMINAL\s*(\d+\.\d+)%', html)
        plazo_sel_match = re.search(r'Selecciona un plazo\s*\n?\s*([\d,]+)\s*d', html)
 
        # Calcular plazo real: plazo = monto * 360 / (principal * tasa/100)
        # Primero necesitamos el principal. Usamos el par conocido del GAT:
        # Si el plazo seleccionado es 360 días con GAT 8.69%, y el monto es $43,450
        # entonces principal = monto * 360 / (plazo * tasa/100)
        principal = 500000  # Default de Finsus
        if gat_match and plazo_sel_match:
            gat_tasa = float(gat_match.group(1))
            plazo_sel = int(plazo_sel_match.group(1).replace(',', ''))
            # Buscar el par con esa tasa
            for monto_str, tasa_str in pares:
                if abs(float(tasa_str) - gat_tasa) < 0.01:
                    monto = float(monto_str.replace(',', ''))
                    principal = round(monto * 360 * 100 / (plazo_sel * gat_tasa))
                    print(f"Finsus principal detectado: ${principal:,.0f}")
                    break
 
        tasas_por_plazo = {}
        if pares:
            for monto_str, tasa_str in pares:
                monto = float(monto_str.replace(',', ''))
                tasa = float(tasa_str)
                if tasa < 3 or tasa > 15:
                    continue
                # Calcular plazo en días
                plazo_calc = round(monto * 360 * 100 / (principal * tasa))
                # Redondear a plazos conocidos de Finsus
                plazos_conocidos = [0, 7, 30, 90, 180, 360, 540, 600, 720, 1080, 1440, 1800]
                plazo_cercano = min(plazos_conocidos, key=lambda p: abs(p - plazo_calc))
                if abs(plazo_cercano - plazo_calc) <= 5:
                    tasas_por_plazo[plazo_cercano] = tasa
        else:
            print("Finsus: no se encontraron pares monto-tasa")
 
        print("Finsus tasas por plazo:", tasas_por_plazo)
 
        # Hero tasa como tasa_principal
        hero_match = re.search(r'[Gg]enera\s*(\d+\.\d+)%', html)
        meta_match = re.search(r'tasa del (\d+\.\d+)%', html, re.IGNORECASE)
        tasa_principal = None
        if hero_match:
            tasa_principal = round(float(hero_match.group(1)), 2)
        elif meta_match:
            tasa_principal = round(float(meta_match.group(1)), 2)
 
        # Obtener tasa a la vista desde la página de cuenta/ahorro
        tasa_vista = None
        try:
            resp_cuenta = requests.get("https://finsus.mx/personas/cuenta", headers=UA, timeout=10)
            resp_cuenta.raise_for_status()
            cuenta_text = resp_cuenta.text
            # Múltiples patrones para capturar la tasa desde HTML estático o meta tags
            patrones_vista = [
                r'[Gg]enera\s*(\d+\.\d+)\s*%',
                r'tasa del (\d+\.\d+)\s*%',
                r'[Rr]endimiento[^%]*?(\d+\.\d+)\s*%',
                r'con\s+(\d+\.\d+)\s*%\s*(?:\*?\s*de\s*)?rendimiento',
                r'Finsus\+?\s*(?:con\s+)?(\d+\.\d+)\s*%',
            ]
            for patron in patrones_vista:
                vista_match = re.search(patron, cuenta_text, re.IGNORECASE)
                if vista_match:
                    val = float(vista_match.group(1))
                    if 3 <= val <= 15:
                        tasa_vista = round(val, 2)
                        break
            print(f"Finsus cuenta a la vista: {tasa_vista}%")
        except Exception as e:
            print("Error Finsus cuenta:", e)
 
        tasas = {
            "a_la_vista": tasa_vista,
            "7_dias": tasas_por_plazo.get(7),
            "1_mes": tasas_por_plazo.get(30),
            "3_meses": tasas_por_plazo.get(90),
            "6_meses": tasas_por_plazo.get(180),
            "1_ano": tasas_por_plazo.get(360),
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
    """Extrae tasas de Klar desde su tabla de comparación de rendimientos.
 
    La página /inversion tiene una tabla estructurada con tasas por plazo:
    - Klar regular: Cuenta 3%, Flexible 6%, Fija 7d 6.10% ... 365d 6.50%
    - Klar Plus: Cuenta 5%, Flexible 8%, Fija 7d 8.10% ... 365d 8.50%
    - Inversión Max (Plus/Platino): 15%
    """
    url = "https://www.klar.mx/inversion"
    try:
        response = requests.get(url, headers=UA, timeout=10)
        response.raise_for_status()
        # Limpiar HTML tags para obtener texto plano (Webflow renderiza con JS pero
        # el contenido de la tabla está en el HTML estático)
        texto_raw = response.text
        texto = re.sub(r'<[^>]+>', '\n', texto_raw)
        texto = re.sub(r'\n{2,}', '\n', texto)
 
        # Extraer tasa máxima del hero: "Inversión Max: 15% de rendimiento"
        tasa_max = None
        max_match = re.search(r'Inversión Max[:\s]*(\d+(?:\.\d+)?)\s*%', texto, re.IGNORECASE)
        if max_match:
            tasa_max = float(max_match.group(1))
 
        # Fallback: buscar "hasta X% de rendimiento anual"
        if not tasa_max:
            hasta_match = re.search(r'hasta\s+(\d+(?:\.\d+)?)\s*%\s*de\s*rendimiento', texto, re.IGNORECASE)
            if hasta_match:
                val = float(hasta_match.group(1))
                if 8 <= val <= 16:
                    tasa_max = val
 
        # Extraer tasas por plazo — usar findall para obtener TODAS las ocurrencias
        # La tabla tiene dos secciones: Klar regular (primera) y Klar Plus/Platino (segunda)
        # Siempre tomamos la MAYOR tasa (Plus/Platino)
        tasas_plazo = {}
        plazo_patterns = [
            (r'Inversión Fija 7 días\s*\n\s*(\d+\.\d+)%', '7_dias'),
            (r'Inversión Fija 30 días\s*\n\s*(\d+\.\d+)%', '1_mes'),
            (r'Inversión Fija 90 días\s*\n\s*(\d+\.\d+)%', '3_meses'),
            (r'Inversión Fija 180 días\s*\n\s*(\d+\.\d+)%', '6_meses'),
            (r'Inversión Fija 365 días\s*\n\s*(\d+\.\d+)%', '1_ano'),
        ]
        for patron, clave in plazo_patterns:
            matches = re.findall(patron, texto)
            if matches:
                # Tomar la más alta (Plus/Platino)
                tasas_plazo[clave] = max(float(m) for m in matches)
 
        # Tasa flexible: tomar la mayor (Plus = 8%)
        flex_matches = re.findall(r'Inversión Flexible\s*\n\s*(\d+(?:\.\d+)?)\s*%', texto)
        if not flex_matches:
            flex_matches = re.findall(r'Inversiones\s*\n\s*(\d+(?:\.\d+)?)\s*%', texto)
        tasa_flexible = max(float(m) for m in flex_matches) if flex_matches else None
 
        # Cuenta: tomar la mayor (Plus = 5%)
        cuenta_matches = re.findall(r'Cuenta\s*\n\s*(\d+(?:\.\d+)?)\s*%', texto)
        tasa_cuenta = max(float(m) for m in cuenta_matches) if cuenta_matches else None
 
        # a_la_vista = tasa_max (Inversión Max 15%) ya que es disponible y el user quiere la mayor
        resultado = {
            "a_la_vista": tasa_max,
            "tasa_max": tasa_max,
            "cuenta": tasa_cuenta,
            "flexible": tasa_flexible,
            **tasas_plazo
        }
        print("Klar resultado:", resultado)
        return resultado
 
    except Exception as e:
        print("Error Klar:", e)
 
    # Fallback: Playwright (parsea tabla completa desde texto renderizado)
    if browser:
        try:
            page = browser.new_page()
            page.goto(url, timeout=30000)
            page.wait_for_load_state("domcontentloaded", timeout=10000)
            page.wait_for_timeout(2000)
            for _ in range(3):
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(500)
            contenido = page.locator("body").inner_text()
            page.close()
 
            tasa_max = None
            max_match = re.search(r'Inversión Max[:\s]*(\d+(?:\.\d+)?)\s*%', contenido, re.IGNORECASE)
            if max_match:
                tasa_max = float(max_match.group(1))
            if not tasa_max:
                hasta_match = re.search(r'hasta\s+(\d+(?:\.\d+)?)\s*%\s*de\s*rendimiento', contenido, re.IGNORECASE)
                if hasta_match and 8 <= float(hasta_match.group(1)) <= 16:
                    tasa_max = float(hasta_match.group(1))
 
            # Tomar siempre las tasas Plus/Platino (mayor)
            tasas_plazo = {}
            plazo_patterns = [
                (r'Inversión Fija 7 días\s*\n\s*(\d+\.\d+)%', '7_dias'),
                (r'Inversión Fija 30 días\s*\n\s*(\d+\.\d+)%', '1_mes'),
                (r'Inversión Fija 90 días\s*\n\s*(\d+\.\d+)%', '3_meses'),
                (r'Inversión Fija 180 días\s*\n\s*(\d+\.\d+)%', '6_meses'),
                (r'Inversión Fija 365 días\s*\n\s*(\d+\.\d+)%', '1_ano'),
            ]
            for patron, clave in plazo_patterns:
                matches = re.findall(patron, contenido)
                if matches:
                    tasas_plazo[clave] = max(float(m) for m in matches)
 
            flex_matches = re.findall(r'(?:Inversión Flexible|Inversiones)\s*\n\s*(\d+(?:\.\d+)?)\s*%', contenido)
            tasa_flexible = max(float(m) for m in flex_matches) if flex_matches else None
 
            resultado = {
                "a_la_vista": tasa_max,
                "tasa_max": tasa_max,
                "flexible": tasa_flexible,
                **tasas_plazo
            }
            print("Klar Playwright resultado:", resultado)
            return resultado
        except Exception as e:
            print("Error Klar Playwright:", e)
 
    return {"a_la_vista": None, "tasa_max": None}
 
# =========================
# MAIN
# =========================
def main():
    os.makedirs("data", exist_ok=True)
 
    # Scrapers que funcionan con requests (sin Playwright)
    mp_tasa = obtener_tasa_mercadopago()
    revolut_tasa = obtener_tasa_revolut()
    klar_tasas = obtener_tasa_klar()
 
    # Scrapers que necesitan Playwright (React SPAs o sitios que bloquean requests)
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
 
        nu_tasas = obtener_tasas_nu(browser)
        finsus_tasas = obtener_tasas_finsus(browser)
        supertasas = obtener_tasas_supertasas(browser)
        openbank_tasa = obtener_tasa_openbank(browser)
 
        browser.close()
 
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
            "a_la_vista": openbank_tasa
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

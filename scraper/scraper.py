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
    base_url = "https://nu.com.mx/cuenta/rendimientos/"

    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        html = requests.get(base_url, headers=headers, timeout=15).text

        # 🔥 Buscar TODOS los chunks JS
        js_files = re.findall(r'src="(/_next/static/chunks/[^"]+\.js)"', html)

        tasas = {
            "a_la_vista": "-",
            "1_semana": "-",
            "1_mes": "-",
            "3_meses": "-",
            "6_meses": "-",
            "cajita_turbo": "-"
        }

        for js_path in js_files:
            full_url = "https://nu.com.mx" + js_path

            try:
                js = requests.get(full_url, headers=headers, timeout=10).text

                # 🔥 Buscar valores directamente en TODO el archivo
                patrones = {
                    "a_la_vista": r'dynamicYield[:"]\s*"?(\d+\.\d+)',
                    "1_semana": r'dynamicYield7Days[:"]\s*"?(\d+\.\d+)',
                    "1_mes": r'dynamicYield28Days[:"]\s*"?(\d+\.\d+)',
                    "3_meses": r'dynamicYield90Days[:"]\s*"?(\d+\.\d+)',
                    "6_meses": r'dynamicYield180Days[:"]\s*"?(\d+\.\d+)',
                    "cajita_turbo": r'dynamicYieldTurbo[:"]\s*"?(\d+\.\d+)'
                }

                for clave, patron in patrones.items():
                    if tasas[clave] == "-":  # solo si aún no se encontró
                        match = re.search(patron, js)
                        if match:
                            tasas[clave] = round(float(match.group(1)), 2)

                # 🔥 Si ya encontró todo, salimos
                if all(v != "-" for v in tasas.values()):
                    break

            except:
                continue

        print("NU tasas detectadas:", tasas)

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

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
import zipfile
from bs4 import BeautifulSoup
import requests

# Usar curl_cffi para imitar el TLS de Chrome en el servidor repodatos.atdt.gob.mx
try:
    from curl_cffi import requests as cffi_requests
    USAR_CFFI = True
except ImportError:
    USAR_CFFI = False

DATASET_ID = "programa_quien_es_quien_precios_2026"
URL_PAGINA_DATASET = f"https://www.datos.gob.mx/dataset/{DATASET_ID}"
URL_API_CKAN = f"https://www.datos.gob.mx/api/3/action/package_show?id={DATASET_ID}"

# Carpeta donde se descargan los archivos de Profeco (QQP/ está en .gitignore): en la raíz del repo, junto a market_scripts/
RUTA_QQP = os.environ.get("QQP_CARPETA") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "QQP")
RUTA_HISTORIAL = "market_data/historial_descargas.json"


def parsear_argumentos():
    parser = argparse.ArgumentParser(
        description="Descarga e ingesta cortes de QQP 2026 desde datos.gob.mx."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulación: lista los recursos disponibles en datos.gob.mx sin descargarlos.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignora el historial de descargas y fuerza la descarga.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limita la descarga a N archivos (ej. --limit 1 para prueba rápida).",
    )
    parser.add_argument(
        "--filter",
        type=str,
        default=None,
        help="Filtra recursos por texto en su nombre o URL (ej. --filter noviembre o --filter b11).",
    )
    parser.add_argument(
        "--no-pipeline",
        action="store_true",
        help="Solo descarga y descomprime en QQP sin ejecutar el pipeline.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Muestra metadatos detallados de cada recurso encontrado.",
    )
    return parser.parse_args()


def formatear_tamano(bytes_val):
    if not bytes_val:
        return "Desconocido"
    try:
        kb = int(bytes_val) / 1024
        if kb < 1024:
            return f"{kb:.1f} KB"
        return f"{kb / 1024:.2f} MB"
    except (ValueError, TypeError):
        return "Desconocido"


def obtener_recursos_datos_gob(sesion, headers, verbose=False):
    recursos = []

    print(f"[PASO 2] Consultando catálogo en: {URL_PAGINA_DATASET} ...")
    try:
        if USAR_CFFI:
            resp_html = cffi_requests.get(URL_PAGINA_DATASET, impersonate="chrome120", headers=headers, timeout=25)
        else:
            resp_html = sesion.get(URL_PAGINA_DATASET, headers=headers, timeout=25)
        resp_html.raise_for_status()
        html = resp_html.text
        print(f"   -> [OK] Catálogo recibido ({len(html)} bytes).")
    except Exception as e:
        raise RuntimeError(f"Error al conectar con datos.gob.mx: {e}")

    soup = BeautifulSoup(html, "html.parser")
    vistos = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        url_completa = urllib.parse.urljoin(URL_PAGINA_DATASET, href)

        es_archivo_directo = any(
            url_completa.lower().split("?")[0].endswith(ext)
            for ext in [".csv", ".zip", ".rar", ".7z"]
        )

        if es_archivo_directo and url_completa not in vistos:
            vistos.add(url_completa)
            contenedor = a.find_parent(["li", "div", "tr", "section"])
            contexto = " ".join(contenedor.get_text().split()) if contenedor else a.get_text().strip()
            contexto = re.sub(r"\s*Descargar\s*$", "", contexto, flags=re.IGNORECASE).strip()
            recursos.append({
                "url": url_completa,
                "nombre_descriptivo": contexto[:90] or os.path.basename(url_completa),
                "formato": os.path.splitext(url_completa.split("?")[0])[1].replace(".", "").upper(),
                "firma_api": None,
                "tamano_api": None,
            })

    patrones_urls = re.findall(
        r'https?://[^"\'\s<>]+?\.(?:csv|zip|rar|7z)(?:\?[^"\'\s<>]*)?',
        html,
        flags=re.IGNORECASE,
    )
    for url_enc in patrones_urls:
        if url_enc not in vistos:
            vistos.add(url_enc)
            recursos.append({
                "url": url_enc,
                "nombre_descriptivo": os.path.basename(urllib.parse.urlparse(url_enc).path),
                "formato": os.path.splitext(url_enc.split("?")[0])[1].replace(".", "").upper(),
                "firma_api": None,
                "tamano_api": None,
            })

    return recursos


def descargar_archivo_repodatos(url, ruta_destino):
    """
    Descarga desde repodatos.atdt.gob.mx evitando el error 403 Forbidden
    mediante cabeceras Referer/Origin de datos.gob.mx, curl_cffi y respaldo con curl.exe.
    """
    headers_descarga = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        ),
        "Accept": "text/csv,application/octet-stream,application/zip,*/*;q=0.8",
        "Accept-Language": "es-MX,es;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.datos.gob.mx/",
        "Origin": "https://www.datos.gob.mx",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Upgrade-Insecure-Requests": "1",
    }

    # 1. Primer intento: curl_cffi impersonando Chrome con stream
    if USAR_CFFI:
        try:
            print("      [Método 1] Descargando con curl_cffi (Chrome TLS + Referer)...")
            resp = cffi_requests.get(
                url,
                headers=headers_descarga,
                impersonate="chrome120",
                stream=True,
                timeout=300,
            )
            if resp.status_code == 200:
                total_bytes = int(resp.headers.get("Content-Length", 0) or 0)
                descargado = 0
                with open(ruta_destino, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=131072):
                        if chunk:
                            f.write(chunk)
                            descargado += len(chunk)
                            if total_bytes > 0:
                                porc = (descargado / total_bytes) * 100
                                sys.stdout.write(
                                    f"\r      Progreso: {porc:5.1f}% ({descargado / (1024*1024):.1f} MB)"
                                )
                                sys.stdout.flush()
                            else:
                                sys.stdout.write(
                                    f"\r      Descargado: {descargado / (1024*1024):.1f} MB"
                                )
                                sys.stdout.flush()
                print("\n      [OK] Descarga completada vía curl_cffi.")
                return True
            else:
                print(f"      -> Código HTTP {resp.status_code} en Método 1. Pasando a Método 2...")
        except Exception as e:
            print(f"      -> Aviso en Método 1 ({e}). Pasando a Método 2...")

    # 2. Segundo intento: curl.exe nativo del sistema operativo Windows
    print("      [Método 2] Descargando con curl.exe nativo de Windows...")
    cmd_curl = [
        "curl.exe",
        "-L",
        "--fail",
        "-A", headers_descarga["User-Agent"],
        "-e", "https://www.datos.gob.mx/",
        "-H", "Accept: text/csv,application/octet-stream,*/*;q=0.8",
        "-H", "Accept-Language: es-MX,es;q=0.9",
        "-o", ruta_destino,
        url,
    ]
    resultado = subprocess.run(cmd_curl)
    if resultado.returncode == 0 and os.path.exists(ruta_destino) and os.path.getsize(ruta_destino) > 1000:
        tam_mb = os.path.getsize(ruta_destino) / (1024 * 1024)
        print(f"      [OK] Descarga completada vía curl.exe ({tam_mb:.2f} MB).")
        return True

    raise RuntimeError(f"No se pudo descargar {url} (403 Forbidden en ambos métodos).")


def main():
    args = parsear_argumentos()

    print("=" * 70)
    print(" MONITOR QQP 2026 - DATOS.GOB.MX (ANTI-403 REPODATOS ATDT)")
    print("=" * 70)
    print(f"[CONFIG] Dataset Objetivo          : {DATASET_ID}")
    print(f"[CONFIG] Modo Simulación (--dry-run): {'SÍ' if args.dry_run else 'NO'}")
    print(f"[CONFIG] Forzar Descarga (--force)  : {'SÍ' if args.force else 'NO'}")
    print(f"[CONFIG] Filtro Texto (--filter)    : {args.filter or 'Ninguno'}")
    print(f"[CONFIG] Límite (--limit)           : {args.limit or 'Sin límite'}")
    print("-" * 70)

    os.makedirs(RUTA_QQP, exist_ok=True)
    os.makedirs("market_data", exist_ok=True)

    if os.path.exists(RUTA_HISTORIAL):
        with open(RUTA_HISTORIAL, "r", encoding="utf-8") as f:
            historial = json.load(f)
        print(f"[PASO 1] Historial cargado: {len(historial)} archivos procesados previamente.")
    else:
        historial = {}
        print(f"[PASO 1] Sin historial previo. Se creará en '{RUTA_HISTORIAL}'.")

    sesion = requests.Session()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-MX,es;q=0.9",
        "Referer": "https://www.datos.gob.mx/",
    }

    try:
        recursos = obtener_recursos_datos_gob(sesion, headers, args.verbose)
    except Exception as e:
        print(f"[ERROR CRÍTICO] {e}")
        sys.exit(1)

    recursos_filtrados = []
    for r in recursos:
        texto_eval = f"{r['nombre_descriptivo']} {r['url']}".lower()
        if any(exc in texto_eval for exc in ["diccionario", "metadato", "catalogo", "catálogo", "leeme", "readme"]):
            continue

        if args.filter and args.filter.lower() not in texto_eval:
            continue

        recursos_filtrados.append(r)

    print(f"[PASO 3] Recursos de precios válidos encontrados: {len(recursos_filtrados)}")

    if not recursos_filtrados:
        print("\n[AVISO] No se encontraron archivos que coincidan con los filtros.")
        sys.exit(0)

    # PASO 4: Verificar contra el historial local
    print("\n[PASO 4] Verificando novedades frente a tu historial local...")
    cola_descarga = []

    for idx, rec in enumerate(recursos_filtrados, 1):
        url = rec["url"]
        parsed = urllib.parse.urlparse(url)
        nombre_archivo = os.path.basename(parsed.path)

        # Usamos el nombre del archivo o URL como firma base (repodatos bloquea peticiones HEAD sin Referer)
        firma_remota = rec["firma_api"] or url
        ya_descargado = (url in historial) and (historial[url] == str(firma_remota))

        if ya_descargado and not args.force:
            estado_str = "OMITIR (Ya en Parquet)"
        else:
            estado_str = "NUEVO / PENDIENTE" + (" [FORZADO]" if args.force else "")
            cola_descarga.append((url, nombre_archivo, str(firma_remota), rec["nombre_descriptivo"]))

        print(f"   [{idx}/{len(recursos_filtrados)}] {nombre_archivo} -> {estado_str}")
        if args.verbose:
            print(f"         Título : {rec['nombre_descriptivo']}")
            print(f"         URL    : {url}")

    if args.limit and len(cola_descarga) > args.limit:
        print(f"\n[LÍMITE] Se recortó la cola a {args.limit} archivo(s).")
        cola_descarga = cola_descarga[: args.limit]

    if args.dry_run:
        print("\n" + "=" * 70)
        print(f" [FIN DE SIMULACIÓN] Archivos pendientes de descarga: {len(cola_descarga)}")
        print("=" * 70)
        sys.exit(0)

    if not cola_descarga:
        print("\n[OK] Tu Parquet ya cuenta con todos los archivos publicados en datos.gob.mx.")
        sys.exit(0)

    # PASO 5: Descargar a QQP
    print(f"\n[PASO 5] Descargando {len(cola_descarga)} archivo(s) hacia '{RUTA_QQP}'...")
    archivos_exitosos = 0

    for url, nombre_archivo, firma_remota, titulo in cola_descarga:
        ruta_destino = os.path.join(RUTA_QQP, nombre_archivo)
        print(f"\n   -> Descargando: {nombre_archivo} ({titulo})...")

        try:
            descargar_archivo_repodatos(url, ruta_destino)

            if ruta_destino.lower().endswith(".zip"):
                print(f"      Descomprimiendo ZIP: {nombre_archivo}...")
                with zipfile.ZipFile(ruta_destino, "r") as z:
                    z.extractall(RUTA_QQP)
                os.remove(ruta_destino)
            elif ruta_destino.lower().endswith(".rar"):
                print(f"      Descomprimiendo RAR: {nombre_archivo}...")
                import patoolib
                patoolib.extract_archive(ruta_destino, outdir=RUTA_QQP)
                os.remove(ruta_destino)

            historial[url] = firma_remota
            archivos_exitosos += 1

            with open(RUTA_HISTORIAL, "w", encoding="utf-8") as f:
                json.dump(historial, f, indent=2)

        except Exception as e:
            print(f"\n      [ERROR] Falló la descarga de {nombre_archivo}: {e}")

    # PASO 6: Disparar procesamiento
    if archivos_exitosos > 0:
        if args.no_pipeline:
            print("\n[MODO --no-pipeline] Archivos listos en la carpeta QQP para revisión manual.")
        else:
            print("\n[PASO 6] Ejecutando pipeline (Ingesta a Parquet y limpieza de QQP -> Modelo -> JSON)...")
            subprocess.run([sys.executable, "market_scripts/procesar_datos.py"], check=True)
            subprocess.run([sys.executable, "market_scripts/Entrenamiento_Masivo.py"], check=True)
            subprocess.run([sys.executable, "market_scripts/exportar_json.py"], check=True)
            print("\n" + "=" * 70)
            print(" ¡PROCESO COMPLETADO! Datos actualizados y carpeta QQP limpia.")
            print("=" * 70)


if __name__ == "__main__":
    main()
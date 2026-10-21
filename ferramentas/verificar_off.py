"""Os códigos testados no celular existem no Open Food Facts? Quanto tempo a resposta leva?"""

import json
import time
import urllib.request

for ean in ["7891800652260", "7500435172561", "7891000053508", "7896005800027"]:
    url = (f"https://world.openfoodfacts.org/api/v2/product/{ean}.json"
           "?fields=product_name,product_name_pt,brands,quantity,image_front_small_url")
    inicio = time.monotonic()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HistoricoPrecosBot/0.1 (verificacao)"})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
            cors = r.headers.get("Access-Control-Allow-Origin")
        ms = int((time.monotonic() - inicio) * 1000)
        print(f"{ean}: {ms} ms, status={d.get('status')} ({d.get('status_verbose')}), CORS={cors}, produto={d.get('product')}")
    except urllib.error.HTTPError as e:
        print(f"{ean}: HTTP {e.code} em {int((time.monotonic() - inicio) * 1000)} ms: {e.read(200)}")
    except Exception as e:
        print(f"{ean}: erro {e}")

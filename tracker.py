"""Relève les prix du NosBazar (via l'API de nosbazar.com) et les ajoute à un CSV.

- Chaque objet de items.json peut avoir plusieurs numéros (vnums) : versions
  différentes du même objet, ou toutes les couleurs d'une même aile. Le prix
  relevé est le plus bas parmi toutes ces versions.
- "freq_h": 3  -> relevé à chaque passage (toutes les 3 h)
  "freq_h": 24 -> relevé une seule fois par jour, au passage de "daily_hour_utc"

Aucune dépendance externe : Python 3.9+ standard suffit.
Usage : python tracker.py            (relevé normal)
        FORCE_ALL=1 python tracker.py (tout relever maintenant)
"""

import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

API_URL = "https://nosbazar.com/api/search"
ROOT = Path(__file__).parent
ITEMS_FILE = ROOT / "items.json"
CSV_FILE = ROOT / "docs" / "data" / "prices.csv"

TOP_N = 10                 # nombre d'offres les moins chères prises pour la moyenne
PAUSE_BETWEEN_ITEMS = 5    # secondes entre deux objets, pour ménager le site
MAX_ATTEMPTS = 3

CSV_HEADER = [
    "date_utc", "serveur", "vnum", "objet",
    "prix_min", "prix_moyen_top", "nb_offres", "quantite_visible", "categorie",
]


def search(server: int, vnums: list[int]) -> list[dict]:
    """Renvoie la 1re page d'annonces pour ces numéros d'objet, triée par prix croissant."""
    body = {
        "server": server,
        "filters": {
            "index": 0,
            "category": 0,
            "sub_category": 0,
            "level": 0,
            "rare": 0,
            "upgrade": 0,
            "order": 0,          # 0 = prix croissant
            "vnum": vnums[:50],  # l'API accepte 50 numéros au maximum
        },
        "lang": "UK",
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "nosbazar-price-tracker (suivi perso, petit volume)",
        },
        method="POST",
    )

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response).get("items", [])
        except urllib.error.HTTPError as err:
            # 429 = file d'attente pleine, 502/503/504 = serveur de jeu lent ou déconnecté
            if err.code in (429, 502, 503, 504) and attempt < MAX_ATTEMPTS:
                time.sleep(30 * attempt)
                continue
            raise
        except urllib.error.URLError:
            if attempt < MAX_ATTEMPTS:
                time.sleep(30 * attempt)
                continue
            raise
    return []


def item_vnums(item: dict) -> list[int]:
    if "vnums" in item:
        return [int(v) for v in item["vnums"]]
    return [int(item["vnum"])]


def is_due(item: dict, config: dict, now: datetime, force: bool) -> bool:
    if force:
        return True
    freq = int(item.get("freq_h", 3))
    if freq <= 3:
        return True
    # relevé quotidien : seulement au passage qui tombe dans le créneau de 3 h
    start = int(config.get("daily_hour_utc", 6))
    return start <= now.hour < start + 3


def main() -> int:
    config = json.loads(ITEMS_FILE.read_text(encoding="utf-8"))
    server = config["server"]
    server_name = config.get("server_name", str(server))
    now_dt = datetime.now(timezone.utc)
    now = now_dt.strftime("%Y-%m-%d %H:%M")
    force = os.environ.get("FORCE_ALL", "").strip() in ("1", "true", "yes")

    due = [it for it in config["items"] if is_due(it, config, now_dt, force)]
    print(f"{len(due)} objet(s) à relever sur {len(config['items'])}")

    CSV_FILE.parent.mkdir(parents=True, exist_ok=True)
    new_file = not CSV_FILE.exists()
    if not new_file:
        # ancien fichier sans la colonne "categorie" : on met l'en-tête à jour
        lines = CSV_FILE.read_text(encoding="utf-8").splitlines()
        if lines and "categorie" not in lines[0]:
            lines[0] = ",".join(CSV_HEADER)
            CSV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    failures = 0

    with CSV_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(CSV_HEADER)

        for i, item in enumerate(due):
            if i:
                time.sleep(PAUSE_BETWEEN_ITEMS)
            vnums = item_vnums(item)
            name = item["name"]
            category = item.get("categorie", "")
            key = "+".join(str(v) for v in vnums)
            try:
                listings = search(server, vnums)
            except Exception as err:  # on note l'échec et on passe à l'objet suivant
                print(f"[ERREUR] {name} ({key}) : {err}", file=sys.stderr)
                failures += 1
                continue

            wanted = set(vnums)
            listings = [l for l in listings if l.get("item_vnum") in wanted]
            prices = sorted(l["bazar_price"] for l in listings)
            if not prices:
                print(f"[INFO] {name} : aucune offre en vente")
                writer.writerow([now, server_name, key, name, "", "", 0, 0, category])
                continue

            top = prices[:TOP_N]
            writer.writerow([
                now, server_name, key, name,
                prices[0], round(mean(top)), len(listings),
                sum(l.get("amount", 0) for l in listings), category,
            ])
            print(f"[OK] {name} : min {prices[0]:,} / moyenne top {len(top)} {round(mean(top)):,}")

    # Échec seulement si TOUS les objets ont échoué (le workflow le signalera)
    return 1 if due and failures == len(due) else 0


if __name__ == "__main__":
    sys.exit(main())

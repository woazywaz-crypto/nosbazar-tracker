"""Relève les prix du NosBazar (via l'API de nosbazar.com) et les ajoute à un CSV.

Aucune dépendance externe : Python 3.9+ standard suffit.
Usage : python tracker.py
"""

import csv
import json
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
    "prix_min", "prix_moyen_top", "nb_offres", "quantite_visible",
]


def search(server: int, vnum: int) -> list[dict]:
    """Renvoie la 1re page d'annonces pour un objet, triée par prix croissant."""
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
            "vnum": [vnum],
        },
        "lang": "UK",
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "nosbazar-price-tracker (suivi perso, 1 requete/objet toutes les 3 h)",
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


def main() -> int:
    config = json.loads(ITEMS_FILE.read_text(encoding="utf-8"))
    server = config["server"]
    server_name = config.get("server_name", str(server))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    CSV_FILE.parent.mkdir(parents=True, exist_ok=True)
    new_file = not CSV_FILE.exists()
    failures = 0

    with CSV_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(CSV_HEADER)

        for i, item in enumerate(config["items"]):
            if i:
                time.sleep(PAUSE_BETWEEN_ITEMS)
            vnum, name = item["vnum"], item["name"]
            try:
                listings = search(server, vnum)
            except Exception as err:  # on note l'échec et on passe à l'objet suivant
                print(f"[ERREUR] {name} ({vnum}) : {err}", file=sys.stderr)
                failures += 1
                continue

            listings = [l for l in listings if l.get("item_vnum") == vnum]
            prices = sorted(l["bazar_price"] for l in listings)
            if not prices:
                print(f"[INFO] {name} : aucune offre en vente")
                writer.writerow([now, server_name, vnum, name, "", "", 0, 0])
                continue

            top = prices[:TOP_N]
            row = [
                now, server_name, vnum, name,
                prices[0], round(mean(top)), len(listings),
                sum(l.get("amount", 0) for l in listings),
            ]
            writer.writerow(row)
            print(f"[OK] {name} : min {prices[0]:,} / moyenne top {len(top)} {round(mean(top)):,}")

    # Échec seulement si TOUS les objets ont échoué (le workflow le signalera)
    return 1 if failures and failures == len(config["items"]) else 0


if __name__ == "__main__":
    sys.exit(main())

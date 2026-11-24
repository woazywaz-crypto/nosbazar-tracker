"""Cherche de nouveaux objets à suivre sur NosBazar (nom exact + prix sur le serveur).

Écrit docs/data/candidats.json : objets pas encore suivis, en vente sur le serveur.
"""
import json, re, time, urllib.parse, urllib.request
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).parent
MOTS = [
    # annonces officielles récentes (NosMall, roues, coffres)
    "lune du désert", "Coffre du destin", "apparences d'arme du désert", "carte de spécialiste en or",
    "Parfum", "ange gardien", "Cylloan", "chance runique", "mère Nature", "précieuse draconique",
    "Clé principale", "amélioration des runes", "Jeu de tarot", "Grimoire d'invocation", "Ancelloan",
    "récupération géante", "Bon de fabrication", "zodiaque", "apôtre", "pain d'épice", "Noël",
    "os de dragon", "Céline", "Forga", "lapin", "licorne", "Nezarun", "Vénus", "raptor",
    # familles déjà suivies : autres versions
    "Coffre d'apparence d'arme", "Boîte aléatoire", "Lot de tenue", "Ensemble de", "Ailes de",
    "Minifamilier", "Tapis volant", "Planche", "Titre",
]

import os
if os.environ.get("MOTS"):
    MOTS = [m.strip() for m in os.environ["MOTS"].split(";") if m.strip()]

def get(url, data=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None,
                                 headers={"Content-Type": "application/json",
                                          "User-Agent": "nosbazar-price-tracker (suivi perso)"},
                                 method="POST" if data else "GET")
    for essai in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as err:
            print("  réessai", essai + 1, err)
            time.sleep(15)
    return None

def main():
    config = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))
    suivis = {v for it in config["items"] for v in it["vnums"]}
    noms = {}
    for mot in MOTS:
        res = get("https://nosbazar.com/api/items/name-search?" +
                  urllib.parse.urlencode({"q": mot, "lang": "FR", "limit": 60}))
        n = 0
        for m in (res or {}).get("matches", []):
            if int(m["vnum"]) in suivis:
                continue
            nom = re.sub(r"\s+", " ", m["name"]).strip()
            noms.setdefault(nom, {"vnums": set(), "mot": mot})["vnums"].add(int(m["vnum"]))
            n += 1
        print(f"{mot}: {n}")
        time.sleep(1)
    print(len(noms), "noms à vérifier")
    out = []
    for i, (nom, d) in enumerate(sorted(noms.items())):
        vnums = sorted(d["vnums"])[:50]
        res = get("https://nosbazar.com/api/search", {
            "server": config["server"], "lang": "UK",
            "filters": {"index": 0, "category": 0, "sub_category": 0, "level": 0, "rare": 0,
                        "upgrade": 0, "order": 0, "vnum": vnums}})
        offres = [l for l in (res or {}).get("items", []) if l.get("item_vnum") in d["vnums"]]
        prix = sorted(l["bazar_price"] for l in offres)
        if prix:
            out.append({"name": nom, "vnums": vnums, "mot": d["mot"], "min": prix[0],
                        "moyenne": round(mean(prix[:10])), "offres": len(offres),
                        "quantite": sum(l.get("amount", 0) for l in offres)})
            print(f"[{i}] {nom}: {prix[0]:,} ({len(offres)} offres)")
        time.sleep(2)
    (ROOT / "docs" / "data" / "candidats.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(out), "candidats en vente")

if __name__ == "__main__":
    main()

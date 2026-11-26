"""Cherche sur NosBazar les objets cités dans les événements NosMall (docs/data/event_noms.json)
et écrit docs/data/event_objets.json avec vnums, nom FR et prix sur le serveur suivi."""
import json, os, re, time, unicodedata, urllib.parse, urllib.request
from pathlib import Path
from statistics import mean
ROOT = Path(__file__).parent

def get(url, data=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None,
                                 headers={"Content-Type": "application/json", "User-Agent": "nosbazar-price-tracker (suivi perso)"},
                                 method="POST" if data else "GET")
    for essai in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as err:
            print("  réessai", essai + 1, err); time.sleep(10)
    return None

def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()

def names(q, lang):
    res = get("https://nosbazar.com/api/items/name-search?" + urllib.parse.urlencode({"q": q, "lang": lang, "limit": 30}))
    return (res or {}).get("matches", [])

def main():
    config = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))
    noms = json.loads((ROOT / os.environ.get("NOMS", "docs/data/event_noms.json")).read_text(encoding="utf-8"))
    out = []
    for i, n in enumerate(noms):
        en = re.sub(r"\s*\((random|limited)[^)]*\)", "", n["en"], flags=re.I)
        lg = "FR" if n.get("fr_src") else "UK"
        ms = names(en, lg)
        exact = [m for m in ms if norm(m["name"]) == norm(n["en"])] or [m for m in ms if norm(m["name"]) == norm(en)]
        pick = exact or [m for m in ms if norm(m["name"]).startswith(norm(en))][:8]
        time.sleep(1)
        if not pick:
            print(f"[{i}] {n['en']}: introuvable"); continue
        vnums = sorted({int(m["vnum"]) for m in pick})[:50]
        if lg == "FR":
            frn = pick[0]["name"]
        else:
            fr = names(str(vnums[0]), "FR"); time.sleep(1)
            frn = next((m["name"] for m in fr if int(m["vnum"]) == vnums[0]), None)
        res = get("https://nosbazar.com/api/search", {"server": config["server"], "lang": "UK",
              "filters": {"index": 0, "category": 0, "sub_category": 0, "level": 0, "rare": 0, "upgrade": 0, "order": 0, "vnum": vnums}})
        offres = [l for l in (res or {}).get("items", []) if l.get("item_vnum") in vnums]
        if i == 0 and offres: print("exemple offre :", {k: v for k, v in offres[0].items()})
        prix = sorted(l["bazar_price"] for l in offres)
        out.append({"en": n["en"], "fr": frn, "uk": pick[0]["name"], "vnums": vnums, "sources": n["sources"],
                    "min": prix[0] if prix else None, "moyenne": round(mean(prix[:10])) if prix else None, "offres": len(offres)})
        print(f"[{i}] {n['en']} -> {frn} {vnums}: {prix[0] if prix else '-'} ({len(offres)})")
        time.sleep(2)
    (ROOT / os.environ.get("SORTIE", "docs/data/event_objets.json")).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(out), "objets trouvés")

if __name__ == "__main__":
    main()

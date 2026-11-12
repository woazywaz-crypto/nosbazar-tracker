"""Ajoute ou retire un objet de items.json à partir du titre d'une « issue » GitHub.

Titres reconnus (créés par les boutons de la page de suivi) :
  Ajouter : <nom exact de l'objet sur NosBazar>
  Retirer : <numéros de l'objet, ex. 13664 ou 4600+4608>   (ou son nom)
Le corps de l'issue peut contenir une ligne « Catégorie : Ailes ».

Écrit :
  - items.json mis à jour
  - $RESULT_FILE : message à poster en réponse
  - $OBJETS_FILE : numéros à relever tout de suite (objet ajouté)
Code de sortie 0 = changement fait, 2 = rien à faire / erreur expliquée dans le message.
"""

import json
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
ITEMS_FILE = ROOT / "items.json"
RESULT_FILE = Path(os.environ.get("RESULT_FILE", "result.md"))
OBJETS_FILE = Path(os.environ.get("OBJETS_FILE", "objets.txt"))


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.replace("œ", "oe").replace("’", "'")
    return re.sub(r"\s+", " ", s).strip().lower()


def key_of(item: dict) -> str:
    return "+".join(str(v) for v in item["vnums"])


def save(config: dict) -> None:
    items = config["items"]
    lines = ["{"]
    for k in ("server", "server_name", "daily_hour_utc"):
        if k in config:
            lines.append(f'  {json.dumps(k)}: {json.dumps(config[k], ensure_ascii=False)},')
    lines.append('  "items": [')
    lines += ["    " + json.dumps(x, ensure_ascii=False) + ("," if i < len(items) - 1 else "")
              for i, x in enumerate(items)]
    lines += ["  ]", "}"]
    ITEMS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def done(msg: str, code: int) -> None:
    RESULT_FILE.write_text(msg, encoding="utf-8")
    print(msg)
    sys.exit(code)


def search(name: str) -> list[dict]:
    url = "https://nosbazar.com/api/items/name-search?" + urllib.parse.urlencode(
        {"q": name, "lang": "FR", "limit": 50})
    req = urllib.request.Request(url, headers={"User-Agent": "nosbazar-price-tracker"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get("matches", [])


def main() -> None:
    title = os.environ.get("TITLE", "").strip()
    body = os.environ.get("BODY", "") or ""
    m = re.match(r"^\s*(ajouter|retirer)\s*:\s*(.+?)\s*$", title, re.I)
    if not m:
        done("Titre non reconnu. Utilise « Ajouter : nom de l'objet » ou « Retirer : numéros ».", 2)
    action, arg = m.group(1).lower(), m.group(2)
    cat_m = re.search(r"cat[ée]gorie\s*:\s*(.+)", body, re.I)
    category = (cat_m.group(1).strip() if cat_m else "") or "Autres"

    config = json.loads(ITEMS_FILE.read_text(encoding="utf-8"))
    items = config["items"]

    if action == "retirer":
        target = arg.replace(" ", "")
        found = [it for it in items if key_of(it) == target or norm(it["name"]) == norm(arg)]
        if not found:
            done(f"❌ « {arg} » n'est pas dans la liste des objets suivis.", 2)
        config["items"] = [it for it in items if it not in found]
        save(config)
        names = ", ".join(f"**{it['name']}**" for it in found)
        done(f"✅ Retiré du suivi : {names}.\n\nSon historique de prix reste enregistré.", 0)

    # --- ajouter ---
    try:
        matches = search(arg)
    except Exception as err:  # NosBazar injoignable
        done(f"❌ Impossible de joindre NosBazar pour trouver « {arg} » ({err}). Réessaie plus tard.", 2)

    exact = [x for x in matches if norm(x["name"]) == norm(arg)]
    if not exact and len(matches) == 1:
        exact = matches
    if not exact:
        if not matches:
            done(f"❌ Aucun objet nommé « {arg} » sur NosBazar. Vérifie l'orthographe (nom en français, comme dans le jeu).", 2)
        sugg = "\n".join(f"- {x['name']}" for x in matches[:15])
        done(f"❌ Pas de correspondance exacte pour « {arg} ». Objets proches :\n\n{sugg}\n\n"
             "Relance l'ajout avec le nom exact.", 2)

    vnums = sorted({int(x["vnum"]) for x in exact})
    key = "+".join(map(str, vnums))
    name = exact[0]["name"]
    if any(key_of(it) == key or set(it["vnums"]) & set(vnums) for it in items):
        done(f"ℹ️ **{name}** est déjà suivi.", 2)
    items.append({"name": name, "categorie": category, "vnums": vnums, "freq_h": 24})
    save(config)
    OBJETS_FILE.write_text(key, encoding="utf-8")
    done(f"✅ Ajouté au suivi : **{name}** (catégorie {category}, numéro {key}).\n\n"
         "Son premier prix vient d'être relevé : recharge ta page de suivi.", 0)


if __name__ == "__main__":
    main()

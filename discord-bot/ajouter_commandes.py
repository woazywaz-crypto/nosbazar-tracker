"""Ajoute les commandes /bonnes-affaires et /investir au bot Discord (à lancer une fois).

Utilise le token du fichier .env de ce dossier (le même que pour l'ancien bot).
Ne touche pas aux commandes /prix et /prix-actualiser.
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent


def lire_token() -> str:
    import os
    if os.environ.get("DISCORD_TOKEN"):
        return os.environ["DISCORD_TOKEN"].strip()
    for nom in (".env", ".env.txt"):
        f = ROOT / nom
        if f.exists():
            for ligne in f.read_text(encoding="utf-8-sig").splitlines():
                if ligne.strip().startswith("DISCORD_TOKEN") and "=" in ligne:
                    return ligne.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def appel(methode: str, url: str, token: str, corps=None):
    req = urllib.request.Request(
        "https://discord.com/api/v10" + url, method=methode,
        data=json.dumps(corps).encode() if corps is not None else None,
        headers={"Authorization": "Bot " + token, "Content-Type": "application/json",
                 "User-Agent": "DiscordBot (nosbazar, 1.0)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


COMMANDES = [{
    "name": "bonnes-affaires",
    "description": "Objets moins chers que d'habitude en ce moment (bons achats)",
    "options": [
        {"type": 4, "name": "jours", "required": False, "min_value": 2, "max_value": 90,
         "description": "Comparer au prix habituel de combien de jours (7 par défaut)"},
        {"type": 4, "name": "nombre", "required": False, "min_value": 1, "max_value": 15,
         "description": "Combien d'objets afficher (10 par défaut)"},
    ],
}, {
    "name": "investir",
    "description": "Meilleurs achats pour un budget, d'après les prix habituels du mois",
    "options": [
        {"type": 4, "name": "budget", "required": True, "min_value": 100000, "max_value": 1000000000000,
         "description": "Somme à investir en or (ex. 1000000000 pour 1 milliard)"},
        {"type": 4, "name": "jours", "required": False, "min_value": 7, "max_value": 90,
         "description": "Période de référence en jours (30 par défaut)"},
    ],
}]


def main() -> None:
    token = lire_token()
    if not token or "colle" in token.lower():
        sys.exit("❌ Token introuvable : mets ce fichier dans le dossier du bot, à côté du fichier .env.")
    try:
        app = appel("GET", "/applications/@me", token)
        noms = [appel("POST", f"/applications/{app['id']}/commands", token, c)["name"] for c in COMMANDES]
    except urllib.error.HTTPError as err:
        sys.exit(f"❌ Discord a refusé ({err.code}) : {err.read().decode(errors='ignore')[:300]}")
    print("✅ Commandes " + ", ".join("/" + n for n in noms) + f" ajoutées au bot {app.get('name', '')}.")
    print("Dans Discord, appuie sur Ctrl+R puis tape /investir.")


if __name__ == "__main__":
    main()

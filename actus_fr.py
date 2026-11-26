"""Télécharge les annonces NosTale Steam en français (2 ans) dans docs/data/actus_fr.json."""
import json, time, urllib.request
from pathlib import Path
H = {"User-Agent": "Mozilla/5.0 nosbazar-tracker (perso)", "Accept-Language": "fr-FR,fr"}
limite = time.time() - 2 * 366 * 86400
out, off, langs = [], 0, {}
while True:
    url = ("https://store.steampowered.com/events/ajaxgetpartnereventspageable/?clan_accountid=0"
           f"&appid=550470&offset={off}&count=100&l=french&origin=https://store.steampowered.com")
    d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=60))
    ev = d.get("events") or []
    if off == 0:
        Path("docs/data/actus_fr_brut.json").write_text(json.dumps(ev[:2], ensure_ascii=False, indent=1))
    if not ev: break
    for e in ev:
        t = e.get("rtime32_start_time") or 0
        b = e.get("announcement_body") or {}
        langs[b.get("language")] = langs.get(b.get("language"), 0) + 1
        out.append({"date": time.strftime("%Y-%m-%d", time.gmtime(t)), "titre": b.get("headline") or e.get("event_name"),
                    "texte": b.get("body", ""), "langue": b.get("language"), "gid": e.get("gid")})
    if min((e.get("rtime32_start_time") or 0) for e in ev) < limite: break
    off += len(ev); time.sleep(1)
out = [x for x in out if x["date"] >= time.strftime("%Y-%m-%d", time.gmtime(limite))]
Path("docs/data/actus_fr.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(out), "annonces, langues:", langs)

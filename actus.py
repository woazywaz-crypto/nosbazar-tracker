"""Télécharge les annonces NosTale (Steam) des 2 dernières années dans docs/data/actus.json."""
import json, time, urllib.request
from pathlib import Path
url = ("https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid=550470&count=2000"
       "&maxlength=0&feeds=steam_community_announcements&format=json")
req = urllib.request.Request(url, headers={"User-Agent": "nosbazar-tracker (perso)"})
items = json.load(urllib.request.urlopen(req, timeout=60))["appnews"]["newsitems"]
limite = time.time() - 2 * 366 * 86400
out = [{"date": time.strftime("%Y-%m-%d", time.gmtime(n["date"])), "titre": n["title"],
        "texte": n["contents"], "url": n["url"]} for n in items if n["date"] >= limite]
Path("docs/data/actus.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(out), "annonces", out[-1]["date"] if out else "")

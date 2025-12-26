import json
import os
from datetime import datetime, timedelta, timezone

import requests

CONTACT_EMAIL = "maik.roth1998@gmail.com"  # optional, falls du das magst
HEADERS = {
    "User-Agent": f"chess-activity-checker/1.0 ({CONTACT_EMAIL})"
}

PLAYERS = ["err_daemon", "m41k", "Kathi_2905"]
DAYS = 2


def get_archives(username: str):
    url = f"https://api.chess.com/pub/player/{username}/games/archives"
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json().get("archives", [])


def get_recent_games(username: str, days: int = 2):
    now_utc = datetime.now(timezone.utc)
    threshold = now_utc - timedelta(days=days)

    archives = get_archives(username)
    if not archives:
        return []

    recent_archives = archives[-3:]
    recent_games = []

    for archive_url in recent_archives:
        try:
            r = requests.get(archive_url, headers=HEADERS, timeout=10)
            r.raise_for_status()
            data = r.json()
        except Exception:
            continue

        for g in data.get("games", []):
            end_ts = g.get("end_time")
            if not end_ts:
                continue

            end_dt = datetime.fromtimestamp(end_ts, tz=timezone.utc)
            if end_dt >= threshold:
                recent_games.append({
                    "url": g.get("url"),
                    "end_time": end_dt.isoformat(),
                    "time_class": g.get("time_class"),
                    "rated": g.get("rated"),
                    "white": (g.get("white") or {}).get("username"),
                    "black": (g.get("black") or {}).get("username"),
                })

    recent_games.sort(key=lambda x: x["end_time"], reverse=True)
    return recent_games


def get_stats(username: str):
    url = f"https://api.chess.com/pub/player/{username}/stats"
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


def get_tactics_info(username: str):
    stats = get_stats(username)
    tactics = stats.get("tactics")
    if not tactics:
        return None, None, None

    last = tactics.get("last") or {}
    highest = tactics.get("highest") or {}
    lowest = tactics.get("lowest") or {}

    current_rating = last.get("rating") or highest.get("rating")
    return (
        current_rating,
        highest.get("rating"),
        lowest.get("rating"),
    )


def analyze_player(username: str, days: int = 2):
    uname_api = username.lower()

    # Spiele
    try:
        games = get_recent_games(uname_api, days=days)
    except Exception:
        games = []

    # Taktik
    try:
        t_cur, t_hi, t_lo = get_tactics_info(uname_api)
    except Exception:
        t_cur, t_hi, t_lo = None, None, None

    active = len(games) > 0

    return {
        "username": username,
        "active_last_days": active,
        "days_window": days,
        "games_count": len(games),
        "games_recent": games[:5],  # nur die letzten 5 anzeigen
        "tactics_current": t_cur,
        "tactics_highest": t_hi,
        "tactics_lowest": t_lo,
    }


def main():
    results = []
    for p in PLAYERS:
        results.append(analyze_player(p, days=DAYS))

    data = {
        "last_update_utc": datetime.now(timezone.utc).isoformat(),
        "days": DAYS,
        "players": results,
    }

    os.makedirs("data", exist_ok=True)
    with open("data/stats.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

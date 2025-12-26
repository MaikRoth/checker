import requests
from datetime import datetime, timedelta, timezone

# ---- Configuration ----
CONTACT_EMAIL = "maik.roth1998@gmail.com"

HEADERS = {
    "User-Agent": f"chess-activity-checker/1.0 ({CONTACT_EMAIL})"
}

PLAYERS = ["err_daemon", "m41k", "Kathi_2905"]

# ---- Colors / Emojis ----
class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    GRAY = "\033[90m"


def title(text):
    bar = "═" * (len(text) + 2)
    print(f"\n{Color.MAGENTA}╔{bar}╗{Color.RESET}")
    print(f"{Color.MAGENTA}║ {Color.BOLD}{text}{Color.RESET}{Color.MAGENTA} ║{Color.RESET}")
    print(f"{Color.MAGENTA}╚{bar}╝{Color.RESET}")


def separator():
    print(f"{Color.GRAY}{'-' * 60}{Color.RESET}")


def badge(text, color):
    return f"{color}[ {text} ]{Color.RESET}"


# ---- API helpers ----

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
                    "end_time": end_dt,
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
    return current_rating, highest.get("rating"), lowest.get("rating")


# ---- Presentation logic ----

def print_player_report(info, days: int = 2):
    uname = info["username"]
    games = info["games"]
    t_cur = info["tactics_current"]
    t_hi = info["tactics_highest"]
    t_lo = info["tactics_lowest"]

    title(f"♟️  Stats für {uname}")

    # Games section
    print(f"{Color.CYAN}{Color.BOLD}🕒 Aktivität der letzten {days} Tage{Color.RESET}")
    separator()

    if not games:
        print(f"{badge('INAKTIV', Color.RED)} {Color.RED}{uname} hat NICHT gespielt.{Color.RESET}")
        print(f"👉 {Color.YELLOW}Zeit, wieder zu spielen – sonst verlierst du deinen Flow! 🔥{Color.RESET}\n")
    else:
        print(f"{badge('AKTIV', Color.GREEN)} {Color.GREEN}{uname} hat {len(games)} Partie(n) gespielt.{Color.RESET}\n")

        for g in games[:5]:
            end_str = g["end_time"].strftime('%Y-%m-%d %H:%M')
            rated = "Rated" if g["rated"] else "Unrated"
            print(
                f"• {Color.BOLD}{end_str}{Color.RESET} "
                f"({g['time_class']}, {rated})\n"
                f"  {Color.GRAY}{g['white']} vs {g['black']}{Color.RESET}"
            )
        print()

    # Tactics section
    print(f"{Color.CYAN}{Color.BOLD}🧠 Taktikwertung{Color.RESET}")
    separator()

    if t_cur is None and t_hi is None and t_lo is None:
        print(f"{badge('KEINE DATEN', Color.YELLOW)} Keine Taktikdaten im API.\n")
    else:
        print(f"⭐ Aktuell:  {Color.BOLD}{t_cur}{Color.RESET}")
        if t_hi is not None:
            print(f"📈 Highest: {t_hi}")
        if t_lo is not None:
            print(f"📉 Lowest:  {t_lo}")
        print()


def analyze_player(username: str, days: int = 2):
    uname = username
    uname_api = username.lower()

    try:
        games = get_recent_games(uname_api, days=days)
    except Exception:
        games = []

    try:
        t_cur, t_hi, t_lo = get_tactics_info(uname_api)
    except Exception:
        t_cur, t_hi, t_lo = None, None, None

    return {
        "username": uname,
        "games": games,
        "tactics_current": t_cur,
        "tactics_highest": t_hi,
        "tactics_lowest": t_lo,
    }


def main():
    days = 2
    results = []

    title("🏆 Chess.com Vergleich – Aktivität & Taktiken")

    for player in PLAYERS:
        info = analyze_player(player, days=days)
        results.append(info)
        print_player_report(info, days=days)

    # Summary
    title("📊 Zusammenfassung")

    for info in results:
        uname = info["username"]
        games = info["games"]
        t = info["tactics_current"]

        if games:
            activity = badge("AKTIV", Color.GREEN)
        else:
            activity = badge("INAKTIV", Color.RED)

        tac = f"{t}" if t is not None else "—"

        print(f"{activity} {Color.BOLD}{uname}{Color.RESET}  |  🧠 Taktik: {tac}")

    # Highest tactics
    players_with_tactics = [i for i in results if i["tactics_current"] is not None]
    if players_with_tactics:
        best = max(players_with_tactics, key=lambda i: i["tactics_current"])
        print(f"\n👑 {Color.BOLD}{best['username']}{Color.RESET} hat aktuell die höchste Taktikwertung: {best['tactics_current']}")

    print()


if __name__ == "__main__":
    main()

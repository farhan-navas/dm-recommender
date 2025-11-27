import re

from datetime import datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from scraper.rate_limiter import fetch


def extract_user_id_from_profile_url(profile_url: str) -> str | None:
    """
    Extract a stable user_id from a XenForo-style member URL.
    Examples:
      /members/some-user.12345/
      https://.../members/some-user.12345/
    Returns the numeric ID as string, or None if not found.
    """
    if not profile_url:
        return None

    path = urlparse(profile_url).path

    # Typical XenForo: /members/username.12345/
    m = re.search(r'\.(\d+)/?$', path)
    if m:
        return m.group(1)

    # Fallback: last group of digits in path
    m = re.search(r'/(\d+)/?$', path)
    if m:
        return m.group(1)

    return None


def _clean_int(value: str | None) -> int | None:
    if not value:
        return None
    digits = re.sub(r"[^0-9]", "", value)
    return int(digits) if digits else None


def parse_user_profile(html: str, profile_url: str, user_id: str | None) -> dict:
    """Parse tooltip HTML for a member into a structured dict."""
    soup = BeautifulSoup(html, "html.parser")
    tooltip = soup.select_one(".memberTooltip")

    # Username (prefer tooltip, fallback to slug)
    username = None
    if tooltip:
        name_el = tooltip.select_one(".memberTooltip-name a.username")
        if name_el:
            username = name_el.get_text(strip=True)
    if not username:
        path = urlparse(profile_url).path.rstrip("/")
        if "." in path:
            username = path.split("/")[-1].split(".")[0]
        else:
            username = path.split("/")[-1] or None

    # User title / role
    role = None
    if tooltip:
        role_el = tooltip.select_one(".userTitle")
        if role_el:
            role = role_el.get_text(strip=True)

    # Joined date is stored in the header pairs
    join_date = None
    if tooltip:
        time_el = tooltip.select_one(".memberTooltip-blurb time")
        if time_el:
            join_date = time_el.get("datetime") or time_el.get_text(strip=True)

    # Collect stats rows (Replies, Discussions, Reaction score, etc.)
    stats: dict[str, str] = {}
    if tooltip:
        for dl in tooltip.select(".memberTooltip-stats dl"):
            dt = dl.find("dt")
            dd = dl.find("dd")
            if not dt or not dd:
                continue
            label = dt.get_text(strip=True).lower()
            value = dd.get_text(" ", strip=True)
            stats[label] = value

    def stat_value(label: str) -> int | None:
        return _clean_int(stats.get(label))

    scraped_at = datetime.now().isoformat(timespec="seconds") + "Z"

    return {
        "user_id": user_id,
        "username": username,
        "profile_url": profile_url,
        "join_date": join_date,
        "role": role,
        "gender": None,
        "country_of_birth": None,
        "replies": stat_value("replies"),
        "discussions_created": stat_value("discussions created"),
        "reaction_score": stat_value("reaction score"),
        "points": stat_value("points"),
        "media_count": stat_value("media"),
        "showcase_count": stat_value("showcase"),
        "scraped_at": scraped_at,
    }


def fetch_user_profile(profile_url: str) -> dict | None:
    """Fetch + parse the public tooltip for a user profile URL."""
    user_id = extract_user_id_from_profile_url(profile_url)
    if not user_id:
        print(f"[user] Could not parse user_id from {profile_url}")
        return None

    tooltip_url = profile_url.rstrip("/") + "/tooltip"
    print(f"[user] Fetching tooltip {tooltip_url} (user_id={user_id})")
    html = fetch(tooltip_url)
    return parse_user_profile(html, profile_url, user_id)


def get_or_fetch_user(profile_url: str, user_cache: dict[str, dict]) -> dict | None:
    """
    Returns a user dict. Uses cache to avoid refetching profiles.
    user_cache: {user_id: user_dict}
    """
    if not profile_url:
        return None

    user_id = extract_user_id_from_profile_url(profile_url)
    if not user_id:
        return None

    if user_id in user_cache:
        return user_cache[user_id]

    profile = fetch_user_profile(profile_url)
    if profile:
        user_cache[user_id] = profile
    return profile

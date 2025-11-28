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


def _as_string(value):
    """Convert BeautifulSoup attribute values (which may be lists) to strings."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        if not value:
            return None
        value = value[0]
    return str(value)


def _collect_stats(pairs: list) -> dict[str, str]:
    stats: dict[str, str] = {}
    for dl in pairs:
        dt = dl.find("dt")
        dd = dl.find("dd")
        if not dt or not dd:
            continue
        label = dt.get_text(strip=True).lower()
        value = dd.get_text(" ", strip=True)
        stats[label] = value
    return stats


def _fallback_username(profile_url: str) -> str | None:
    path = urlparse(profile_url).path.rstrip("/")
    if "." in path:
        return path.split("/")[-1].split(".")[0]
    return path.split("/")[-1] or None


def _build_user_record(
    *,
    user_id: str | None,
    profile_url: str,
    username: str | None,
    join_date: str | None,
    role: str | None,
    stats: dict[str, str],
) -> dict:
    def stat_value(label: str) -> int | None:
        return _clean_int(stats.get(label))

    scraped_at = datetime.now().isoformat(timespec="seconds") + "Z"

    return {
        "user_id": user_id,
        "username": username or _fallback_username(profile_url),
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


def _has_meaningful_profile_data(user: dict) -> bool:
    metric_keys = [
        "replies",
        "discussions_created",
        "reaction_score",
        "points",
        "media_count",
        "showcase_count",
    ]
    if any(user.get(k) is not None for k in metric_keys):
        return True
    return bool(user.get("join_date") or user.get("role"))


def parse_user_profile_page(html: str, profile_url: str, user_id: str | None) -> dict | None:
    """Attempt to extract user data from the full profile page."""
    soup = BeautifulSoup(html, "html.parser")

    username = None
    header = soup.select_one("h1.p-title-value") or soup.select_one(".memberHeader-title")
    if header:
        username = header.get_text(strip=True)
    if not username:
        name_el = soup.select_one(".memberHeader-content .username")
        if name_el:
            username = name_el.get_text(strip=True)

    role = None
    role_el = soup.select_one(".memberHeader-content .userTitle") or soup.select_one(".userTitle")
    if role_el:
        role = role_el.get_text(strip=True)

    join_date = None
    time_el = soup.select_one(".memberHeader-content time") or soup.find("time", attrs={"itemprop": "dateCreated"})
    if time_el:
        join_date = _as_string(time_el.get("datetime")) or time_el.get_text(strip=True)

    stats = _collect_stats(soup.select("dl.pairs"))
    if not join_date:
        join_date = stats.get("joined")

    user = _build_user_record(
        user_id=user_id,
        profile_url=profile_url,
        username=username,
        join_date=join_date,
        role=role,
        stats=stats,
    )

    return user if _has_meaningful_profile_data(user) else None


def parse_user_tooltip(html: str, profile_url: str, user_id: str | None) -> dict:
    """Parse tooltip HTML for a member into a structured dict."""
    soup = BeautifulSoup(html, "html.parser")
    tooltip = soup.select_one(".memberTooltip")

    username = None
    if tooltip:
        name_el = tooltip.select_one(".memberTooltip-name a.username")
        if name_el:
            username = name_el.get_text(strip=True)

    role = None
    if tooltip:
        role_el = tooltip.select_one(".userTitle")
        if role_el:
            role = role_el.get_text(strip=True)

    join_date = None
    if tooltip:
        time_el = tooltip.select_one(".memberTooltip-blurb time")
        if time_el:
            join_date = _as_string(time_el.get("datetime")) or time_el.get_text(strip=True)

    stats = _collect_stats(tooltip.select(".memberTooltip-stats dl") if tooltip else [])

    return _build_user_record(
        user_id=user_id,
        profile_url=profile_url,
        username=username,
        join_date=join_date,
        role=role,
        stats=stats,
    )


def fetch_user_profile(profile_url: str) -> dict | None:
    """Prefer full profile page; fallback to tooltip when blocked."""
    user_id = extract_user_id_from_profile_url(profile_url)
    if not user_id:
        print(f"[user] Could not parse user_id from {profile_url}")
        return None

    try:
        profile_html = fetch(profile_url)
    except Exception as exc:  # noqa: BLE001 - fallback to tooltip on any failure
        print(f"[user] Error fetching profile page {profile_url}: {exc}")
        profile_html = None

    if profile_html:
        profile = parse_user_profile_page(profile_html, profile_url, user_id)
        if profile:
            return profile
        print(f"[user] Profile page lacked data for {profile_url}, falling back to tooltip")

    tooltip_url = profile_url.rstrip("/") + "/tooltip"
    print(f"[user] Fetching tooltip {tooltip_url} (user_id={user_id})")
    tooltip_html = fetch(tooltip_url)
    return parse_user_tooltip(tooltip_html, profile_url, user_id)


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

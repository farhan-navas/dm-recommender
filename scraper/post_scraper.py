# post_scraper.py

import csv
import hashlib
import re
from pathlib import Path

from bs4 import BeautifulSoup

from scraper.rate_limiter import fetch
from scraper.user_scraper import (get_or_fetch_user, extract_user_id_from_profile_url)

BASE_URL = "https://www.personalitycafe.com"

# Thread index selectors
THREAD_CARD_SELECTOR = "div.structItem--thread"
THREAD_LINK_SELECTOR = "h3.structItem-title a"

# Post selectors
POST_SELECTOR = "article.js-post"
USERNAME_SELECTOR = ".MessageCard__user-info__name"
BODY_SELECTOR = ".message-body .bbWrapper"


def absolute_url(href: str) -> str:
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return BASE_URL + href
    return BASE_URL + "/" + href.lstrip("/")


def _is_member_link(href: str | None) -> bool:
    """Return True when href looks like a member profile link."""
    return bool(href and "/members/" in href)


def get_thread_list(
    forum_url: str,
    max_pages: int = 3,
    thread_limit: int | None = 5,
):
    """
    Scrape a forum section index to collect thread URLs.
    `max_pages` prevents infinite crawling; increase carefully.
    `thread_limit` stops once N unique threads are gathered (default 5).
    """
    seen = set()
    ordered_threads: list[str] = []
    page_url = forum_url

    for page in range(1, max_pages + 1):
        print(f"[threads] Fetching forum index page {page}: {page_url}")
        html = fetch(page_url)
        soup = BeautifulSoup(html, "html.parser")

        for card in soup.select(THREAD_CARD_SELECTOR):
            link = card.select_one(THREAD_LINK_SELECTOR)
            if not link:
                continue
            href = link.get("href")
            if isinstance(href, list):
                href = href[0]
            if not href:
                continue
            url = absolute_url(str(href))
            if url in seen:
                continue
            seen.add(url)
            ordered_threads.append(url)
            if thread_limit is not None and len(ordered_threads) >= thread_limit:
                break

        if thread_limit is not None and len(ordered_threads) >= thread_limit:
            break

        # Find "next page" (if any)
        next_link = soup.find("a", rel="next")
        if not next_link:
            break
        next_href = next_link.get("href")
        if isinstance(next_href, list):
            next_href = next_href[0]
        if not next_href:
            break
        page_url = absolute_url(str(next_href))

    print(f"[threads] Collected {len(ordered_threads)} thread URLs.")
    return ordered_threads


def get_thread_pages(thread_url: str, max_pages: int = 20):
    """
    Return a list of URLs for all pages inside a thread.
    """
    pages = [thread_url]
    page_url = thread_url

    for page in range(2, max_pages + 1):
        print(f"[thread-pages] Checking for page {page} of thread {thread_url}")
        html = fetch(page_url)
        soup = BeautifulSoup(html, "html.parser")
        next_link = soup.find("a", rel="next")
        if not next_link:
            break
        next_href = next_link.get("href")
        if isinstance(next_href, list):
            next_href = next_href[0]
        if not next_href:
            break
        page_url = absolute_url(str(next_href))
        pages.append(page_url)

    return pages


def _extract_post_id(post_div) -> str | None:
    """
    Try to extract a stable post_id from attributes.
    Common patterns: data-content, id="js-post-123", id="post-123", etc.
    """
    # 1) data-content
    pid = post_div.get("data-content")
    if pid:
        return str(pid)

    # 2) id with digits
    elem_id = post_div.get("id")
    if elem_id:
        m = re.search(r"(\d+)$", elem_id)
        if m:
            return m.group(1)

    return None


def parse_posts_from_page(html: str):
    """
    Parse posts from one thread page.
    Returns a list of dicts:
      {
        "post_id",
        "username",
        "profile_url",
        "timestamp",
        "text",
      }
    """
    soup = BeautifulSoup(html, "html.parser")

    # Optional: debug HTML to inspect if selectors break
    digest = hashlib.sha1(html.encode("utf-8", "ignore")).hexdigest()
    debug_path = Path("debug_html") / f"page-{digest}.html"
    debug_path.parent.mkdir(parents=True, exist_ok=True)
    with open(debug_path, "w", encoding="utf-8") as debug_file:
        debug_file.write(soup.prettify())

    posts = []

    for idx, post_div in enumerate(soup.select(POST_SELECTOR), start=1):
        # Username
        user_el = post_div.select_one(USERNAME_SELECTOR)
        username = user_el.get_text(strip=True) if user_el else post_div.get("data-author")

        # Profile URL
        profile_url = None
        if user_el:
            link_el = user_el.find("a", href=True)
            if link_el:
                profile_url = absolute_url(str(link_el["href"]))
        if not profile_url:
            # Fallback: any link to /members/ inside post card
            link_el = post_div.find("a", href=_is_member_link)
            if link_el and link_el.get("href"):
                profile_url = absolute_url(str(link_el["href"]))

        # Timestamp
        time_el = post_div.find("time", attrs={"datetime": True}) or post_div.find("time")
        timestamp = time_el.get("datetime") if time_el else None

        # Body text
        body_el = post_div.select_one(BODY_SELECTOR)
        text = body_el.get_text("\n", strip=True) if body_el else None

        # Post ID
        post_id = _extract_post_id(post_div)

        posts.append({
            "post_id": post_id,
            "username": username,
            "profile_url": profile_url,
            "timestamp": timestamp,
            "text": text,
        })

        # TODO: REMOVE THIS LATER, THIS JUST FOR TESTING!
        if idx >= 5:
            break

    return posts


def scrape_thread(thread_url: str, user_cache: dict[str, dict], max_pages: int = 20):
    """
    Scrape all posts in a thread and enrich with user_id via user_cache.
    Returns list of post dicts with keys:
      thread_url, page_url, post_id, user_id, username, timestamp, text
    """
    all_posts = []
    pages = get_thread_pages(thread_url, max_pages=max_pages)

    for page_url in pages:
        print(f"[scrape-thread] Fetching page {page_url}")
        html = fetch(page_url)
        page_posts = parse_posts_from_page(html)

        for p in page_posts:
            profile_url = p.get("profile_url")
            user_id = None
            username = p.get("username")

            if profile_url:
                user = get_or_fetch_user(profile_url, user_cache)
                if user:
                    user_id = user["user_id"]
                    # Prefer canonical username from profile if present
                    if user.get("username"):
                        username = user["username"]
                else:
                    # fallback: derive from URL
                    user_id = extract_user_id_from_profile_url(profile_url)

            post_row = {
                "thread_url": thread_url,
                "page_url": page_url,
                "post_id": p.get("post_id"),
                "user_id": user_id,
                "username": username,
                "timestamp": p.get("timestamp"),
                "text": p.get("text"),
            }
            all_posts.append(post_row)

    print(f"[scrape-thread] Got {len(all_posts)} posts from {thread_url}")
    return all_posts

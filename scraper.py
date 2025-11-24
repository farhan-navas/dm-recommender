import hashlib

from bs4 import BeautifulSoup
from rate_limiter import fetch

BASE_URL = "https://www.personalitycafe.com"
THREAD_CARD_SELECTOR = "div.structItem--thread"
THREAD_LINK_SELECTOR = "h3.structItem-title a"

POST_SELECTOR = "article.js-post"
USERNAME_SELECTOR = ".MessageCard__user-info__name"
BODY_SELECTOR = ".message-body .bbWrapper"

def absolute_url(href: str) -> str:
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return BASE_URL + href
    return BASE_URL + "/" + href.lstrip("/")


def get_thread_list(forum_url: str, max_pages: int = 3, thread_limit: int | None = 5):
    """
    Scrape a forum section index to collect thread URLs.
    `max_pages` prevents infinite crawling; increase carefully.
    `thread_limit` stops once N unique threads are gathered (default 5).
    """
    seen = set()
    ordered_threads = []
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

if __name__ == "__main__":
    forum_url = "https://www.personalitycafe.com/forums/myers-briggs-forum.49/"
    thread_urls = get_thread_list(forum_url, max_pages=5)
    print(f"Fetched {len(thread_urls)} threads for manual testing")

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


def parse_posts_from_page(html: str):
    """
    Parse posts from one thread page.
    Adjust CSS selectors according to actual HTML.
    """
    soup = BeautifulSoup(html, "html.parser")

    digest = hashlib.sha1(html.encode("utf-8", "ignore")).hexdigest()
    debug_path = f"output-{digest}.txt"
    with open(debug_path, "w", encoding="utf-8") as debug_file:
        debug_file.write(soup.prettify())
    posts = []

    for post_div in soup.select(POST_SELECTOR):
        user_el = post_div.select_one(USERNAME_SELECTOR)
        username = user_el.get_text(strip=True) if user_el else post_div.get("data-author")

        time_el = post_div.find("time", attrs={"datetime": True}) or post_div.find("time")
        timestamp = time_el.get("datetime") if time_el else None

        body_el = post_div.select_one(BODY_SELECTOR)
        text = body_el.get_text("\n", strip=True) if body_el else None

        posts.append({
            "username": username,
            "timestamp": timestamp,
            "text": text,
        })

    return posts


def scrape_thread(thread_url: str):
    all_posts = []
    pages = get_thread_pages(thread_url)

    for page_url in pages:
        print(f"[scrape-thread] Fetching page {page_url}")
        html = fetch(page_url)
        posts = parse_posts_from_page(html)
        for p in posts:
            p["thread_url"] = thread_url
            p["page_url"] = page_url
        all_posts.extend(posts)

    print(f"[scrape-thread] Got {len(all_posts)} posts from {thread_url}")
    return all_posts


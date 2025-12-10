import csv
import re
from pathlib import Path
from urllib.parse import urlparse

from scraper.data_model import (
    INTERACTIONS_FIELDNAMES,
    POSTS_FIELDNAMES,
    THREADS_FIELDNAMES,
    USERS_FIELDNAMES,
)
from scraper.post_scraper import absolute_url, get_thread_list, scrape_thread

FORUMS_CSV_PATH = Path("forums.csv")

def _slug_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    if not path:
        return "forums"
    tail = path.split("/")[-1]
    cleaned = re.sub(r"\.\d+$", "", tail)
    return cleaned or "forums"

def load_forums(csv_path: Path) -> list[dict[str, str]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Forums CSV not found at {csv_path}")

    forums: list[dict[str, str]] = []
    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            href = row.get("forum_href")
            name = row.get("forum_name") or href or "unknown"
            if not href:
                continue
            forums.append({"forum_name": name, "forum_href": absolute_url(str(href))})
    return forums

def scrape_single_forum(
    *,
    forum_name: str,
    forum_url: str,
    max_forum_pages: int | None,
    thread_limit: int | None,
    thread_page_limit: int | None,
):
    slug = _slug_from_url(forum_url)
    threads_csv_path = f"threads-{slug}.csv"
    posts_csv_path = f"posts-{slug}.csv"
    users_csv_path = f"users-{slug}.csv"
    interactions_csv_path = f"interactions-{slug}.csv"

    print(f"[main] Scraping forum '{forum_name}' ({forum_url})")

    thread_urls = get_thread_list(
        forum_url,
        max_pages=max_forum_pages,
        thread_limit=thread_limit,
    )
    print(f"[main] Fetched {len(thread_urls)} thread URLs for {forum_name}")

    user_cache: dict[str, dict] = {}
    written_user_ids: set[str] = set()

    with (
        open(posts_csv_path, "w", newline="", encoding="utf-8") as posts_f,
        open(interactions_csv_path, "w", newline="", encoding="utf-8") as interactions_f,
        open(threads_csv_path, "w", newline="", encoding="utf-8") as threads_f,
        open(users_csv_path, "w", newline="", encoding="utf-8") as users_f,
    ):
        posts_writer = csv.DictWriter(posts_f, fieldnames=POSTS_FIELDNAMES)
        posts_writer.writeheader()

        interactions_writer = csv.DictWriter(interactions_f, fieldnames=INTERACTIONS_FIELDNAMES)
        interactions_writer.writeheader()

        threads_writer = csv.DictWriter(threads_f, fieldnames=THREADS_FIELDNAMES)
        threads_writer.writeheader()

        users_writer = csv.DictWriter(users_f, fieldnames=USERS_FIELDNAMES)
        users_writer.writeheader()

        for i, t_url in enumerate(thread_urls, start=1):
            print(f"[main] ({i}/{len(thread_urls)}) Scraping thread: {t_url}")
            try:
                posts, interactions, thread_row = scrape_thread(
                    t_url,
                    user_cache,
                    max_pages=thread_page_limit,
                    forum_url=forum_url,
                )
            except Exception as exc:  # noqa: BLE001 - continue on thread failure
                print(f"[main] Error scraping {t_url}: {exc}")
                continue

            for row in posts:
                posts_writer.writerow(row)

            for interaction in interactions:
                interactions_writer.writerow(interaction)

            threads_writer.writerow(thread_row)

            for user_id, user in user_cache.items():
                if not user_id or user_id in written_user_ids:
                    continue
                users_writer.writerow(user)
                written_user_ids.add(user_id)

    print(
        "[main] Finished forum '{0}'. Outputs: {1}, {2}, {3}, {4}".format(
            forum_name, posts_csv_path, users_csv_path, interactions_csv_path, threads_csv_path
        )
    )

def main() -> None:
    # Common limits for every forum; set to small values while testing.
    max_forum_pages = None
    thread_limit = None
    thread_page_limit = None

    forums = load_forums(FORUMS_CSV_PATH)
    print(f"[main] Loaded {len(forums)} forums from {FORUMS_CSV_PATH}")

    for forum in forums:
        scrape_single_forum(
            forum_name=forum["forum_name"],
            forum_url=forum["forum_href"],
            max_forum_pages=max_forum_pages,
            thread_limit=thread_limit,
            thread_page_limit=thread_page_limit,
        )


if __name__ == "__main__":
    main()

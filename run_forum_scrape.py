import csv

from scraper.data_model import (
    INTERACTIONS_FIELDNAMES,
    POSTS_FIELDNAMES,
    USERS_FIELDNAMES,
)
from scraper.post_scraper import get_thread_list, scrape_thread

def main():
    # Config
    forum_url = "https://www.personalitycafe.com/forums/myers-briggs-forum.49/"
    max_forum_pages = 3
    thread_limit = 1
    thread_page_limit = 10
    posts_csv_path = "posts.csv"
    users_csv_path = "users.csv"
    interactions_csv_path = "interactions.csv"

    # Collect thread URLs
    thread_urls = get_thread_list(
        forum_url,
        max_pages=max_forum_pages,
        thread_limit=thread_limit,
    )
    print(f"[main] Fetched {len(thread_urls)} thread URLs")

    user_cache: dict[str, dict] = {}

    # Scrape posts + users + interactions
    with (
        open(posts_csv_path, "w", newline="", encoding="utf-8") as posts_f,
        open(interactions_csv_path, "w", newline="", encoding="utf-8") as interactions_f,
    ):
        posts_writer = csv.DictWriter(posts_f, fieldnames=POSTS_FIELDNAMES)
        posts_writer.writeheader()

        interactions_writer = csv.DictWriter(interactions_f, fieldnames=INTERACTIONS_FIELDNAMES)
        interactions_writer.writeheader()

        for i, t_url in enumerate(thread_urls, start=1):
            print(f"[main] ({i}/{len(thread_urls)}) Scraping thread: {t_url}")
            try:
                posts, interactions = scrape_thread(t_url, user_cache, max_pages=thread_page_limit)
            except Exception as e:
                print(f"[main] Error scraping {t_url}: {e}")
                continue

            for row in posts:
                posts_writer.writerow(row)
            for interaction in interactions:
                interactions_writer.writerow(interaction)

    # Write users.csv
    with open(users_csv_path, "w", newline="", encoding="utf-8") as users_f:
        users_writer = csv.DictWriter(users_f, fieldnames=USERS_FIELDNAMES)
        users_writer.writeheader()
        for user in user_cache.values():
            users_writer.writerow(user)

    print(f"[main] Done. Wrote {posts_csv_path}, {users_csv_path}, and {interactions_csv_path}")

if __name__ == "__main__":
    main()

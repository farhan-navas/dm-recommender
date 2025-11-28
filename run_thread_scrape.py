"""Run the scraper against a single thread URL."""

import csv

from scraper.post_scraper import scrape_thread


def main() -> None:
    # --- Config ---
    thread_url = "https://www.personalitycafe.com/threads/ask-an-istj-relationship-question-thread.63195/"
    thread_page_limit = 10
    posts_csv_path = "posts.csv"
    users_csv_path = "users.csv"

    user_cache: dict[str, dict] = {}

    posts_fieldnames = [
        "thread_url",
        "page_url",
        "post_id",
        "user_id",
        "username",
        "timestamp",
        "text",
    ]
    users_fieldnames = [
        "user_id",
        "username",
        "profile_url",
        "join_date",
        "role",
        "gender",
        "country_of_birth",
        "replies",
        "discussions_created",
        "reaction_score",
        "points",
        "media_count",
        "showcase_count",
        "scraped_at",
    ]

    print(f"[single-thread] Scraping {thread_url} (max_pages={thread_page_limit})")
    posts = scrape_thread(thread_url, user_cache, max_pages=thread_page_limit)

    with open(posts_csv_path, "w", newline="", encoding="utf-8") as posts_f:
        writer = csv.DictWriter(posts_f, fieldnames=posts_fieldnames)
        writer.writeheader()
        for row in posts:
            writer.writerow(row)

    with open(users_csv_path, "w", newline="", encoding="utf-8") as users_f:
        writer = csv.DictWriter(users_f, fieldnames=users_fieldnames)
        writer.writeheader()
        for user in user_cache.values():
            writer.writerow(user)

    print(f"[single-thread] Done. Wrote {posts_csv_path} and {users_csv_path}")


if __name__ == "__main__":
    main()

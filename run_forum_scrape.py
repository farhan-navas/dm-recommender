import csv
from scraper.post_scraper import get_thread_list, scrape_thread

def main():
    # Config
    forum_url = "https://www.personalitycafe.com/forums/myers-briggs-forum.49/"
    max_forum_pages = 3
    thread_limit = 1
    thread_page_limit = 10
    posts_csv_path = "posts.csv"
    users_csv_path = "users.csv"

    # Collect thread URLs
    thread_urls = get_thread_list(
        forum_url,
        max_pages=max_forum_pages,
        thread_limit=thread_limit,
    )
    print(f"[main] Fetched {len(thread_urls)} thread URLs")

    # Prepare CSV writers
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

    user_cache: dict[str, dict] = {}

    # Scrape posts + users 
    with open(posts_csv_path, "w", newline="", encoding="utf-8") as posts_f:
        posts_writer = csv.DictWriter(posts_f, fieldnames=posts_fieldnames)
        posts_writer.writeheader()

        for i, t_url in enumerate(thread_urls, start=1):
            print(f"[main] ({i}/{len(thread_urls)}) Scraping thread: {t_url}")
            try:
                posts = scrape_thread(t_url, user_cache, max_pages=thread_page_limit)
            except Exception as e:
                print(f"[main] Error scraping {t_url}: {e}")
                continue

            for row in posts:
                posts_writer.writerow(row)

    # Write users.csv
    with open(users_csv_path, "w", newline="", encoding="utf-8") as users_f:
        users_writer = csv.DictWriter(users_f, fieldnames=users_fieldnames)
        users_writer.writeheader()
        for user in user_cache.values():
            users_writer.writerow(user)

    print(f"[main] Done. Wrote {posts_csv_path} and {users_csv_path}")

if __name__ == "__main__":
    main()

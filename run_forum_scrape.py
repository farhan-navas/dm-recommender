import csv

from scraper.data_model import (
    INTERACTIONS_FIELDNAMES,
    POSTS_FIELDNAMES,
    THREADS_FIELDNAMES,
    USERS_FIELDNAMES,
)
from scraper.post_scraper import get_thread_list, scrape_thread

def main():
    curr_forum = "myers-briggs-forum.49/"
    forum_url = f"https://www.personalitycafe.com/forums/{curr_forum}"
    # TODO: for testing, we can set limits here, eg: 3, 1, 10
    max_forum_pages = None
    thread_limit = None
    thread_page_limit = None
    threads_csv_path = f"threads-{curr_forum}.csv"
    posts_csv_path = f"posts-{curr_forum}.csv"
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
    written_user_ids : set[str] = set()

    # Scrape posts + users + interactions + threads
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

            except Exception as e:
                print(f"[main] Error scraping {t_url}: {e}")
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
        f"[main] Done. Wrote {posts_csv_path}, {users_csv_path}, {interactions_csv_path}, and {threads_csv_path}"
    )

if __name__ == "__main__":
    main()

import csv

from scraper import get_thread_list, scrape_thread

def main():
    forum_url = "https://www.personalitycafe.com/forums/myers-briggs-forum.49/"
    thread_urls = get_thread_list(forum_url, max_pages=5)

    with open("personalitycafe_scrape.csv", "w", newline="", encoding="utf-8") as f:
        fieldnames = ["thread_url", "page_url", "username", "timestamp", "text"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i, t_url in enumerate(thread_urls, start=1):
            print(f"[main] ({i}/{len(thread_urls)}) Scraping thread {t_url}")
            try:
                posts = scrape_thread(t_url)
            except Exception as e:
                print(f"[main] Error scraping {t_url}: {e}")
                continue

            for row in posts:
                writer.writerow(row)

    print("[main] Done!")


if __name__ == "__main__":
    main()

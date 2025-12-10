import csv

from bs4 import BeautifulSoup

from scraper.post_scraper import absolute_url
from scraper.rate_limiter import fetch

FORUM_INDEX_URL = "https://www.personalitycafe.com/forums/"
OUTPUT_CSV = "forums.csv"


def parse_forums(html: str) -> list[dict[str, str | None]]:
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict[str, str | None]] = []
    print(f"[parse-forums] Now parsing forums")

    num_forums = 0
    for node in soup.select("div.node-main"):
        num_forums += 1
        link = node.select_one("h3.node-title a")
        if not link:
            continue

        href = link.get("href")
        name = link.get_text(strip=True)
        results.append(
            {
                "forum_name": name,
                "forum_href": str(href),
            }
        )

    print(f"[parse-forums] Overall number of forums is {num_forums}")
    return results

def main() -> None:
    print(f"[forums] Fetching {FORUM_INDEX_URL}")
    html = fetch(FORUM_INDEX_URL)
    forums = parse_forums(html)

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["forum_name", "forum_href"])
        writer.writeheader()
        for forum in forums:
            writer.writerow(forum)

    print(f"[forums] Collected {len(forums)} forums -> {OUTPUT_CSV}")


if __name__ == "__main__":
    main()

import csv

from bs4 import BeautifulSoup

from scraper.rate_limiter import fetch

FORUM_INDEX_URL = "https://www.personalitycafe.com/forums/"
OUTPUT_CSV = "forums-logged-in.csv"

def parse_forums(html) -> list[dict[str, str | None]]:
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict[str, str | None]] = []
    print(f"[parse-forums] Now parsing forums")

    num_forums = 0
    for node in soup.select("div.node-body"):
        num_forums += 1
        main_link = node.select_one("div.node-main h3.node-title a")
        if main_link:
            results.append({"forum_name": main_link.get_text(strip=True),
                            "forum_href": main_link.get("href")}) # type: ignore

        for sub in node.select("ol.subNodeMenu a.subNodeLink"):
            results.append({"forum_name": sub.get_text(strip=True),
                            "forum_href": sub.get("href")}) # type: ignore

    print(f"[parse-forums] Overall number of forums is {num_forums}")
    return results

def main() -> None:
    print(f"[forums] Fetching {FORUM_INDEX_URL}")
    # html = fetch(FORUM_INDEX_URL)
    forums = None
    with open("sample_html/forums-page-logged-in.html", "r") as html:
        forums = parse_forums(html)

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["forum_index", "forum_name", "forum_href"])
        writer.writeheader()
        for idx, forum in enumerate(forums):
            row = {"forum_index": idx, **forum}
            writer.writerow(row)

    print(f"[forums] Collected {len(forums)} forums -> {OUTPUT_CSV}")


if __name__ == "__main__":
    main()

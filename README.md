# DM Recommender Scraper

Lightweight Python scraper that collects thread posts and public user metadata from PersonalityCafe without authentication (all public data).

## Initial DB Schema

Even though the pipeline currently writes CSVs, we treat them as two normalized tables so they can drop directly into a lightweight Postgres instance later.

### `Thread`

| column       | type        | notes                                                               |
| ------------ | ----------- | ------------------------------------------------------------------- |
| `thread_id`  | text        | Hash or slug extracted from `thread_url` (e.g., last path segment). |
| `thread_url` | text        | Canonical PersonalityCafe URL.                                      |
| `forum_url`  | text        | Parent forum listing used when crawling.                            |
| `first_seen` | timestamptz | When the scraper first encountered the thread.                      |
| `last_seen`  | timestamptz | When the thread was last re-scraped.                                |
| `scraped_at` | timestamptz | Timestamp for the current extraction batch.                         |

### `Post`

| column       | type        | notes                                                                        |
| ------------ | ----------- | ---------------------------------------------------------------------------- |
| `post_id`    | text        | XenForo identifier (last digits of `data-content` / `id`). Primary key.      |
| `thread_id`  | text        | FK → `thread.thread_id`.                                                     |
| `page_url`   | text        | Concrete page that was scraped (thread pagination aware).                    |
| `user_id`    | text        | FK → `user.user_id`.                                                         |
| `username`   | text        | Username displayed on the post (overwritten by tooltip version when cached). |
| `timestamp`  | timestamptz | Raw value from `<time datetime>`; ISO 8601 string when stored in CSV.        |
| `text`       | text        | Post body flattened to newline-separated plain text.                         |
| `scraped_at` | timestamptz | When this particular post row was emitted by the scraper.                    |

### `User`

| column                | type        | notes                                                  |
| --------------------- | ----------- | ------------------------------------------------------ |
| `user_id`             | text        | Stable numeric identifier parsed from the member slug. |
| `username`            | text        | Canonical username from tooltip header.                |
| `profile_url`         | text        | Fully-qualified profile link without `/tooltip`.       |
| `join_date`           | timestamptz | Tooltip-provided ISO datetime.                         |
| `role`                | text        | Tooltip “user title” (e.g., Banned, Member).           |
| `gender`              | text/null   | Pulled from the `About` tab when present.              |
| `country_of_birth`    | text/null   | Pulled from the `About` tab when present.              |
| `location`            | text/null   | “From …” location from the profile header/`About` tab. |
| `mbti_type`           | text/null   | Myers-Briggs type string (`About` tab).                |
| `enneagram_type`      | text/null   | Enneagram string (`About` tab).                        |
| `socionics`           | text/null   | Socionics designation, when users fill it out.         |
| `occupation`          | text/null   | Free-form occupation field from the `About` tab.       |
| `replies`             | integer     | Tooltip “Replies” count.                               |
| `discussions_created` | integer     | Tooltip “Discussions created” count.                   |
| `reaction_score`      | integer     | Tooltip “Reaction score”.                              |
| `points`              | integer     | Tooltip “Points”.                                      |
| `media_count`         | integer     | Tooltip “Media” uploads.                               |
| `showcase_count`      | integer     | Tooltip “Showcase items”.                              |
| `scraped_at`          | timestamptz | When this profile snapshot was saved.                  |

# TODO: add following + follower lists

CSV rows store blanks for `NULL` values so they load cleanly later.

### `Interaction` (derived)

To capture edges between users, we derive an interaction row any time a post is a direct reply/quote/mention of another post. The first pass can infer interactions by:

1. Matching quoted blocks (they include the original username + post id in markup).
2. Falling back to explicit `@username` mentions when a quote is absent.

Schema:

| column             | type        | notes                                                                                        |
| ------------------ | ----------- | -------------------------------------------------------------------------------------------- |
| `interaction_id`   | uuid        | Synthetic PK                                                                                 |
| `replying_post_id` | text        | FK → `post.post_id` (the reply), source post id                                              |
| `target_post_id`   | text        | FK → `post.post_id` (the quoted/mentioned post). Nullable when we only know the target user. |
| `source_user_id`   | text        | FK → `user.user_id`, the person replying                                                     |
| `target_user_id`   | text        | FK → `user.user_id`, the person that is being replied to                                     |
| `thread_id`        | text        | Convenience FK for filtering.                                                                |
| `interaction_type` | text        | Enum (`quote`, `mention`, `implicit_reply`).                                                 |
| `confidence`       | numeric     | Between 0–1; `1` for explicit quotes, lower when inferred heuristically.                     |
| `scraped_at`       | timestamptz | Timestamp applied when emitting the derived edge.                                            |

## Running scraper

Orchestrator lives in `scraper/post_scraper.py`. Can be executed directly or via `main.py`:

```bash
python3 run_forum_scrape.py
# or
uv run run_forum_scrape.py
```

Default settings (inside `scraper.post_scraper.main`) crawl the Myers-Briggs forum, respect a conservative rate limit (polite scraping! for now, one request every 3s), and emit the CSVs in the project root.

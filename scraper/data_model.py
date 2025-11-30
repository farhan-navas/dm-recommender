"""Shared schema metadata for CSV outputs."""

POSTS_FIELDNAMES: list[str] = [
    "thread_url",
    "page_url",
    "post_id",
    "user_id",
    "username",
    "timestamp",
    "text",
]

USERS_FIELDNAMES: list[str] = [
    "user_id",
    "username",
    "profile_url",
    "join_date",
    "role",
    "gender",
    "country_of_birth",
    "location",
    "mbti_type",
    "enneagram_type",
    "socionics",
    "occupation",
    "replies",
    "discussions_created",
    "reaction_score",
    "points",
    "media_count",
    "showcase_count",
    "scraped_at",
]

import csv

def count_unique_ids(csv_path, col1, col2):
    unique_ids = set()

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            v1 = row.get(col1)
            v2 = row.get(col2)

            if v1:
                unique_ids.add(v1.strip())
            if v2:
                unique_ids.add(v2.strip())

    print(f"Total unique IDs across '{col1}' and '{col2}': {len(unique_ids)}")
    # return unique_ids

csv_file = "data/interactions-{...}.csv"
col_a = "source_user_id"
col_b = "target_user_id"
unique = count_unique_ids(csv_file, col_a, col_b)
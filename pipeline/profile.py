from collections import Counter

from pipeline.common import DERIVED, RESULTS, iter_jsonl, write_json


def main():
    users = Counter()
    folders = Counter()
    tz = Counter()
    years = Counter()
    ids = set()
    files = 0
    bad_dates = 0
    missing_ids = 0
    for rec in iter_jsonl(DERIVED / "messages.jsonl.gz"):
        files += 1
        users[rec["user"]] += 1
        top = rec["folder"].split("/")[0] if rec["folder"] else "(root)"
        folders[top] += 1
        tz[rec["tz"] or "none"] += 1
        if rec["date_utc"]:
            years[rec["date_utc"][:4]] += 1
        else:
            bad_dates += 1
        if rec["message_id"]:
            ids.add(rec["message_id"])
        else:
            missing_ids += 1
    profile = {
        "files": files,
        "users": len(users),
        "distinct_message_ids": len(ids),
        "missing_message_ids": missing_ids,
        "unparseable_or_out_of_range_dates": bad_dates,
        "messages_per_year_utc": dict(sorted(years.items())),
        "timezone_offsets": dict(tz.most_common()),
        "top_folders": dict(folders.most_common(25)),
        "largest_mailboxes": dict(users.most_common(25)),
        "median_mailbox_files": sorted(users.values())[len(users) // 2],
    }
    write_json(RESULTS / "profile.json", profile)
    for key in ("files", "users", "distinct_message_ids", "unparseable_or_out_of_range_dates"):
        print(key, profile[key])


if __name__ == "__main__":
    main()

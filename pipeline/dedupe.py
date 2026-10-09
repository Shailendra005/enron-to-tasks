import gzip
import json
from collections import defaultdict

from pipeline.common import DERIVED, RESULTS, cluster_key, iter_jsonl, norm_addr, norm_subject, write_json


def main():
    seen = set()
    seen_no_date = set()
    user_cluster = set()
    ids = set()
    cluster_users = defaultdict(set)
    files = 0
    out_path = DERIVED / "index.jsonl.gz"
    with gzip.open(out_path, "wt", encoding="utf-8") as fh:
        for rec in iter_jsonl(DERIVED / "messages.jsonl.gz"):
            files += 1
            cid = cluster_key(rec)
            seen_no_date.add(cluster_key(rec, with_date=False))
            rep = cid not in seen
            seen.add(cid)
            user_cluster.add((rec["user"], cid))
            cluster_users[cid].add(rec["user"])
            if rec["message_id"]:
                ids.add(rec["message_id"])
            row = {
                "path": rec["path"],
                "user": rec["user"],
                "folder": rec["folder"],
                "message_id": rec["message_id"],
                "date_utc": rec["date_utc"],
                "from": norm_addr(rec["from"]),
                "subject": norm_subject(rec["subject"]),
                "cluster": cid,
                "rep": rep,
            }
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    multi_user = sum(1 for users in cluster_users.values() if len(users) > 1)
    stats = {
        "files": files,
        "distinct_message_ids": len(ids),
        "content_clusters": len(seen),
        "content_clusters_ignoring_date": len(seen_no_date),
        "within_mailbox_copies": files - len(user_cluster),
        "cross_mailbox_copies": len(user_cluster) - len(seen),
        "clusters_found_in_more_than_one_mailbox": multi_user,
        "unique_share_of_files": round(len(seen) / files, 4),
    }
    write_json(RESULTS / "dedupe.json", stats)
    for key, value in stats.items():
        print(key, value)


if __name__ == "__main__":
    main()

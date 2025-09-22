import json

src = "data/chatbi_5000_faqs_clean.json"
dst = "data/faqs.jsonl"

with open(src, "r", encoding="utf-8") as f:
    data = json.load(f)

with open(dst, "w", encoding="utf-8") as f:
    for row in data:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

print(f"Converted {len(data)} records to {dst}")

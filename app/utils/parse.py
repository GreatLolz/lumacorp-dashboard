import json

def parse_jsonl(path: str) -> dict:
    with open(path, "r", encoding="utf-8", buffering=1024*1024) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
        
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Skipping invalid line: {e}")
                continue
            yield obj
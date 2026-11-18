"""transcript.py - the one transcript parser (srt, vtt, whisper json).

This file is copied verbatim into every skill folder that reads transcripts (yt-edit, yt-chapters,
yt-retention) so each skill works when copied on its own. tests/test_tools.py fails if the copies
drift apart. Edit yt-edit/transcript.py, then run tests/sync.sh.
"""
import json, re


def parse_ts(s):
    s = s.strip().replace(",", ".")
    p = s.split(":")
    return int(p[0]) * 3600 + int(p[1]) * 60 + float(p[2]) if len(p) == 3 else int(p[0]) * 60 + float(p[1])


def load(path):
    """Return [(start, end, text)] from an .srt, .vtt or whisper .json file."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        raw = fh.read()
    if path.endswith(".json"):
        d = json.loads(raw)
        segs = d.get("segments", d if isinstance(d, list) else [])
        return [(float(s["start"]), float(s["end"]), (s.get("text") or "").strip()) for s in segs]
    cues, cur = [], None
    for line in raw.splitlines():
        m = re.match(r"\s*(\d[\d:.,]+)\s*-->\s*(\d[\d:.,]+)", line)
        if m:
            cur = [parse_ts(m.group(1)), parse_ts(m.group(2)), []]
            cues.append(cur)
        elif cur is not None and line.strip() and not line.strip().isdigit():
            cur[2].append(line.strip())
    return [(a, b, " ".join(t)) for a, b, t in cues if t]

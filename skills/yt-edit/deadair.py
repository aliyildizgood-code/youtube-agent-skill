#!/usr/bin/env python3
"""deadair.py - an edit decision list from a timestamped transcript.

    python3 deadair.py transcript.srt            # or .vtt, or whisper .json
    python3 deadair.py transcript.srt --floor 0.35 --json

Finds three things and prints the cuts as a list you can act on, newest problem first:
  DEAD    gaps between spoken cues longer than the floor
  FILLER  cues that are only filler ("um", "you know", "so yeah"; a lone "Right." is kept)
  REPEAT  a sentence restarted - the second take of the same opening

WHAT IT DOES NOT DO. It does not cut the file. It prints an EDL, the total it would remove, and the
runtime you would land on, and you apply it in whatever editor you use. Nothing here touches media.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fillers that are never an answer on their own, and softer ones that only count when the cue is
# nothing BUT filler words ("so yeah", "okay so"). A lone "Right." or "Okay." is usually a real beat
# of the conversation, so it is left alone.
STRICT = {"um", "umm", "uh", "uhh", "er", "erm", "ah", "hmm", "mm"}
STRICT_PHRASES = ("you know", "i mean", "let me see", "hold on")
SOFT = {"so", "okay", "ok", "right", "yeah", "like", "anyway", "basically", "actually"}


def is_filler(text):
    t = " " + " ".join(re.findall(r"[a-z']+", text.lower())) + " "
    for ph in STRICT_PHRASES:
        t = t.replace(" " + ph + " ", " <strict> ")
    toks = t.split()
    if not toks:
        return False
    if all(w in STRICT or w == "<strict>" for w in toks):
        return True
    return len(toks) >= 2 and all(w in STRICT or w in SOFT or w == "<strict>" for w in toks)


from transcript import load  # noqa: E402  (shared parser, copied into each skill)

def norm(t): return re.sub(r"[^a-z ]", "", t.lower()).split()

def main():
    a = sys.argv[1:]
    as_json = "--json" in a; a = [x for x in a if x != "--json"]
    floor = float(a[a.index("--floor") + 1]) if "--floor" in a else 0.45
    a = [x for x in a if not x.startswith("--") and not re.match(r"^[\d.]+$", x)]
    if not a or not os.path.exists(a[0]): print(__doc__); sys.exit(1)
    cues = load(a[0])
    if not cues: print("no cues found - is this an srt, vtt or whisper json?"); sys.exit(1)
    dur = cues[-1][1]
    cuts = []
    for i, (s, e, t) in enumerate(cues):
        if is_filler(t):
            cuts.append({"kind": "FILLER", "start": s, "end": e, "why": t.strip()[:48]})
        if i:
            gap = s - cues[i - 1][1]
            if gap > floor:
                keep = floor / 2
                cuts.append({"kind": "DEAD", "start": round(cues[i - 1][1] + keep, 3),
                             "end": round(s - keep, 3), "why": f"{gap:.2f}s gap"})
        # A restart is compared against the last cue that was actually SPEECH. Comparing against
        # the literal previous cue misses every retake with an "um" between the two attempts, which
        # is most of them.
        if t.strip() and not is_filler(t):
            j = i - 1
            while j >= 0 and (is_filler(cues[j][2]) or not cues[j][2].strip()): j -= 1
            if j >= 0:
                a1, b1 = norm(cues[j][2])[:5], norm(t)[:5]
                if len(a1) >= 3 and a1 == b1:
                    cuts.append({"kind": "REPEAT", "start": cues[j][0], "end": cues[j][1],
                                 "why": f'restart of "{" ".join(a1)}"'})
    cuts = [c for c in cuts if c["end"] > c["start"]]
    cuts.sort(key=lambda c: c["start"])
    # overlapping cuts are one cut: merge so the removed total is never double counted
    merged = []
    for c in cuts:
        if merged and c["start"] < merged[-1]["end"]:
            m = merged[-1]
            m["end"] = max(m["end"], c["end"])
            if c["kind"] not in m["kind"].split("+"): m["kind"] += "+" + c["kind"]
            m["why"] += "; " + c["why"]
        else:
            merged.append(dict(c))
    cuts = merged
    removed = sum(c["end"] - c["start"] for c in cuts)
    if as_json:
        print(json.dumps({"source": a[0], "duration": dur, "cuts": cuts,
                          "removed": round(removed, 3), "out": round(dur - removed, 3)}, indent=1)); return
    print(f"\n  {a[0]}   {dur:.2f}s in, {len(cues)} cues, dead-air floor {floor}s\n")
    for c in cuts:
        print(f"    {c['kind']:<12} {c['start']:8.2f} -> {c['end']:8.2f}   {c['end']-c['start']:5.2f}s   {c['why']}")
    print(f"\n  {len(cuts)} cuts, {removed:.2f}s removed, {dur - removed:.2f}s out "
          f"({removed / dur * 100:.1f}% shorter)\n")

if __name__ == "__main__":
    main()

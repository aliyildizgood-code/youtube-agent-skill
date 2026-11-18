#!/usr/bin/env python3
"""retention.py - read a YouTube Studio audience-retention export and find the leaks.

    python3 retention.py retention.csv
    python3 retention.py retention.csv --transcript transcript.srt   # names what was said at each drop
    python3 retention.py retention.csv --duration 612                # video length in seconds
    python3 retention.py retention.csv --json

If the export's x-axis is a percentage, the tool needs the video length to talk in seconds. Pass
--duration, or pass --transcript and the length is read from its last cue. With neither, positions
stay in percent, the hook window is the first 10% of the video, and --transcript cannot be used.

Get the file from Studio: Analytics -> a video -> Engagement -> the audience-retention chart ->
the download icon -> "Audience retention". Two columns, a position (percent or seconds) and a
percentage still watching.

Thresholds (25% / 40% lost in the opening) are rules of thumb, not measured per video length.

It reports three things, because they are three different problems with three different fixes:
  HOOK LEAK    what you lost in the first 30 seconds
  CLIFFS       single steep drops - a specific moment people left at
  SLIDE        the steady bleed rate across the flat middle

With --transcript it prints what you were saying at each cliff, which is the only version of this
report you can act on without scrubbing the video yourself.
"""
import csv, json, os, re, sys

def load_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
        for r in csv.reader(fh):
            nums = []
            for c in r:
                c = c.strip().replace("%", "").replace(",", "")
                try: nums.append(float(c))
                except ValueError: nums.append(None)
            vals = [n for n in nums if n is not None]
            if len(vals) >= 2: rows.append((vals[0], vals[1]))
    return rows

def find_cliffs(rows, cutoff_note=None):
    """Cliffs are intervals losing viewers much faster than the typical interval, with adjacent
    steep intervals merged into one. A uniformly steady slide therefore has no cliffs."""
    xs = [r[0] for r in rows]; ys = [r[1] for r in rows]
    iv = []
    for i in range(1, len(rows)):
        d = ys[i - 1] - ys[i]
        span = (xs[i] - xs[i - 1]) or 1
        iv.append((xs[i - 1], xs[i], d, d / span))
    rates = sorted(r[3] for r in iv if r[3] > 0)
    if not rates: return [], iv
    typical = rates[len(rates) // 2]
    steep = [r[2] > 0.8 and r[3] >= 2.5 * typical for r in iv]
    cliffs, i = [], 0
    while i < len(iv):
        if steep[i]:
            j = i
            while j + 1 < len(iv) and steep[j + 1]: j += 1
            cliffs.append((iv[i][0], iv[j][1], sum(x[2] for x in iv[i:j + 1])))
            i = j + 1
        else:
            i += 1
    cliffs.sort(key=lambda c: -c[2])
    return cliffs[:5], iv


def main():
    a = sys.argv[1:]
    as_json = "--json" in a; a = [x for x in a if x != "--json"]
    tr = a[a.index("--transcript") + 1] if "--transcript" in a else None
    dur = float(a[a.index("--duration") + 1]) if "--duration" in a and a.index("--duration") + 1 < len(a) else None
    skip = {tr, str(a[a.index("--duration") + 1]) if "--duration" in a and a.index("--duration") + 1 < len(a) else None}
    files = [x for x in a if not x.startswith("--") and x not in skip]
    if not files or not os.path.exists(files[0]): print(__doc__); sys.exit(1)
    rows = load_csv(files[0])
    if len(rows) < 8: print("could not read at least 8 data points from that csv"); sys.exit(1)
    xs = [r[0] for r in rows]; ys = [r[1] for r in rows]
    pct_axis = max(xs) <= 100.5
    cues = []
    if tr and os.path.exists(tr):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from transcript import load as load_cues
        cues = load_cues(tr)
        if dur is None and pct_axis and cues: dur = cues[-1][1]
    def at(x): return (x / 100.0 * dur) if (pct_axis and dur) else (None if pct_axis else x)
    start = ys[0] or 100.0
    # HOOK: the first 30 seconds; with a percent axis and no length, the first 10% of the video
    cutoff = 30.0 if not pct_axis else (30.0 / dur * 100 if dur else 10.0)
    hook_end = min((y for x, y in rows if x <= cutoff), default=start)
    hook_leak = start - hook_end
    found, iv = find_cliffs(rows)
    cliffs = [{"from": round(f, 2), "to": round(t, 2), "lost": round(d, 2),
               "at_seconds": round(at(f), 1) if at(f) is not None else None}
              for f, t, d in found]
    mid = [r[3] for r in iv if r[0] >= cutoff and not any(c[0] <= r[0] < c[1] for c in found)]
    slide = sum(mid) / len(mid) if mid else 0
    said = {}
    for c in cliffs:
        if c["at_seconds"] is None or not cues: continue
        t = c["at_seconds"]
        near = [q[2] for q in cues if q[0] <= t + 4 and q[1] >= t - 4]
        said[str(c["from"])] = " ".join(near)[:140]
    note = None
    if tr and not cues: note = "transcript had no readable cues"
    elif tr and pct_axis and dur is None: note = "percent axis and no video length: pass --duration"
    out = {"points": len(rows), "start": start, "hook_leak": round(hook_leak, 2),
           "end": ys[-1], "cliffs": cliffs, "slide_per_unit": round(slide, 3), "said": said,
           "hook_window": "first 30s" if (not pct_axis or dur) else "first 10% of video", "note": note}
    if as_json: print(json.dumps(out, indent=1)); return
    print(f"\n  {files[0]}   {len(rows)} points   {ys[0]:.1f}% -> {ys[-1]:.1f}%\n")
    verdict = "healthy" if hook_leak < 25 else "leaking" if hook_leak < 40 else "severe"
    print(f"  HOOK LEAK   {hook_leak:.1f}% lost in the opening   [{verdict}]")
    window = "first 30 seconds" if (not pct_axis or dur) else "first 10% of the video (no --duration given)"
    print(f"              measured over the {window}. Rule of thumb: under 25 is healthy.\n")
    if note: print(f"  NOTE        {note}\n")
    print("  CLIFFS      the moments people actually left")
    for c in cliffs:
        where = f"{c['at_seconds']:.0f}s" if c["at_seconds"] is not None else f"{c['from']}"
        print(f"    -{c['lost']:5.1f}%  at {where:>8}" + (f"   \"{said.get(str(c['from']),'')}\"" if said else ""))
    if not cliffs: print("    none steeper than 0.8% - the loss is all slide, not moments")
    print(f"\n  SLIDE       {slide:.3f}% per unit across the middle")
    print( "              a flat slide is pacing, not content. Cut the middle, do not rewrite it.\n")

if __name__ == "__main__":
    main()

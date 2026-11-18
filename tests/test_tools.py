"""Tests for the six tools. Standard library only:  python3 -m unittest discover -s tests -v"""
import json, os, shutil, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SK = os.path.join(ROOT, "skills")


def run(script, *args, cwd=None):
    p = subprocess.run([sys.executable, script, *args], capture_output=True, text=True, cwd=cwd)
    return p.returncode, p.stdout, p.stderr


def srt(cues):
    return "".join(f"{i + 1}\n{a} --> {b}\n{t}\n\n" for i, (a, b, t) in enumerate(cues))


CUES = [("00:00:00,000", "00:00:03,000", "Hey guys welcome to the video"),
        ("00:00:03,200", "00:00:06,000", "Today I will show you how I got 400 subs"),
        ("00:00:06,100", "00:00:06,600", "um"),
        ("00:00:07,000", "00:00:10,000", "Today I will show you how I got 400 subs in a week"),
        ("00:00:10,500", "00:00:11,000", "Right."),
        ("00:00:14,000", "00:00:20,000", "First thing is the thumbnail and the title"),
        ("00:00:20,200", "00:00:30,000", "Second we talk about retention curves and pacing"),
        ("00:00:36,000", "00:00:45,000", "Third the upload schedule and consistency matters"),
        ("00:00:45,200", "00:00:55,000", "Finally the budget and equipment for editing")]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.srt = self.write("t.srt", srt(CUES))

    def write(self, name, text):
        p = os.path.join(self.tmp, name)
        with open(p, "w") as fh:
            fh.write(text)
        return p


class TranscriptParsing(Base):
    def setUp(self):
        super().setUp()
        sys.path.insert(0, os.path.join(SK, "yt-edit"))
        import transcript
        self.t = transcript

    def test_srt(self):
        c = self.t.load(self.srt)
        self.assertEqual(len(c), len(CUES))
        self.assertAlmostEqual(c[1][0], 3.2)

    def test_vtt_with_header_ids_and_settings(self):
        p = self.write("t.vtt", "WEBVTT\n\n1\n00:01.000 --> 00:03.500 align:start\nhello there\n\n"
                                "00:03.500 --> 00:05.000\nsecond\n")
        c = self.t.load(p)
        self.assertEqual([x[2] for x in c], ["hello there", "second"])
        self.assertAlmostEqual(c[0][0], 1.0)

    def test_whisper_json(self):
        p = self.write("t.json", json.dumps({"segments": [{"start": 0, "end": 2.5, "text": " hi "}]}))
        self.assertEqual(self.t.load(p), [(0.0, 2.5, "hi")])


class DeadAir(Base):
    def cuts(self, *extra):
        rc, out, _ = run(os.path.join(SK, "yt-edit", "deadair.py"), self.srt, "--json", *extra)
        self.assertEqual(rc, 0)
        return json.loads(out)

    def test_finds_repeat_filler_and_dead_air(self):
        d = self.cuts()
        kinds = " ".join(c["kind"] for c in d["cuts"])
        for k in ("REPEAT", "FILLER", "DEAD"):
            self.assertIn(k, kinds)
        self.assertAlmostEqual(d["out"], d["duration"] - d["removed"], places=2)

    def test_lone_right_is_not_filler_but_so_yeah_is(self):
        sys.path.insert(0, os.path.join(SK, "yt-edit"))
        import deadair
        self.assertFalse(deadair.is_filler("Right."))
        self.assertFalse(deadair.is_filler("Okay"))
        self.assertTrue(deadair.is_filler("so yeah"))
        self.assertTrue(deadair.is_filler("Um,"))
        self.assertTrue(deadair.is_filler("you know"))
        self.assertFalse(deadair.is_filler("you know what happened next"))

    def test_cuts_never_overlap(self):
        cs = self.cuts()["cuts"]
        for a, b in zip(cs, cs[1:]):
            self.assertLessEqual(a["end"], b["start"])


class Chapters(Base):
    def test_valid_and_starts_at_zero(self):
        rc, out, _ = run(os.path.join(SK, "yt-chapters", "chapters.py"), self.srt, "--target", "3", "--json")
        d = json.loads(out)
        self.assertTrue(d["valid"])
        self.assertEqual(d["chapters"][0]["start"], 0)
        self.assertTrue(all(c["seconds"] >= 10 for c in d["chapters"]))


def retention_csv(pairs):
    return "pos,pct\n" + "\n".join(f"{x},{y}" for x, y in pairs)


class Retention(Base):
    def go(self, pairs, *extra):
        p = self.write("r.csv", retention_csv(pairs))
        rc, out, err = run(os.path.join(SK, "yt-retention", "retention.py"), p, "--json", *extra)
        self.assertEqual(rc, 0, err)
        return json.loads(out)

    def test_flat_slide_has_no_cliffs(self):
        d = self.go([(i * 10, 100 - i * 5) for i in range(11)])
        self.assertEqual(d["cliffs"], [])

    def test_single_cliff_found_once_even_if_two_steep_samples(self):
        ys = [100, 96, 93, 90, 60, 35, 33, 31, 29, 27, 25]
        d = self.go([(i * 10, y) for i, y in enumerate(ys)])
        self.assertEqual(len(d["cliffs"]), 1)
        self.assertEqual((d["cliffs"][0]["from"], d["cliffs"][0]["to"]), (30, 50))
        self.assertAlmostEqual(d["cliffs"][0]["lost"], 55)

    def test_percent_axis_duration_from_transcript_names_what_was_said(self):
        ys = [100, 96, 93, 90, 60, 58, 56, 54, 52, 50, 48]
        d = self.go([(i * 10, y) for i, y in enumerate(ys)], "--transcript", self.srt)
        self.assertEqual(d["cliffs"][0]["at_seconds"], 16.5)  # 30% of 55s
        self.assertTrue(d["said"])

    def test_percent_axis_without_length_says_so(self):
        ys = [100, 96, 93, 90, 60, 58, 56, 54, 52, 50, 48]
        bad = self.write("empty.srt", "")
        d = self.go([(i * 10, y) for i, y in enumerate(ys)], "--transcript", bad)
        self.assertIsNotNone(d["note"])
        self.assertEqual(d["hook_window"], "first 10% of video")

    def test_duration_flag(self):
        ys = [100, 96, 93, 90, 60, 58, 56, 54, 52, 50, 48]
        d = self.go([(i * 10, y) for i, y in enumerate(ys)], "--duration", "600")
        self.assertEqual(d["cliffs"][0]["at_seconds"], 180.0)

    def test_seconds_axis_hook_window(self):
        d = self.go([(i * 15, 100 - i * 2) for i in range(10)])
        self.assertEqual(d["hook_window"], "first 30s")


class HookScore(Base):
    def score(self, hook):
        rc, out, _ = run(os.path.join(SK, "yt-script", "hookscore.py"), "--hook", hook, "--json")
        return json.loads(out)[0]

    def test_strong_beats_weak(self):
        strong = self.score("You are losing 40% of viewers in 10 seconds, and nobody tells you why")
        weak = self.score("Hey guys welcome to my amazing video")
        self.assertGreater(strong["verdict"], weak["verdict"])

    def test_mid_sentence_like_is_not_penalised(self):
        a = self.score("Nobody told you why 90 percent of channels die in year one")["properties"]["SPECIFICITY"]
        b = self.score("Nobody told you why 90 percent of channels die in year one like this")["properties"]["SPECIFICITY"]
        self.assertEqual(a, b)

    def test_before_is_not_double_counted(self):
        import re
        sys.path.insert(0, os.path.join(SK, "yt-script"))
        import hookscore
        self.assertFalse(hookscore.CURIOSITY.search("before"))

    def test_missing_hook_value_is_a_clean_error(self):
        rc, out, err = run(os.path.join(SK, "yt-script", "hookscore.py"), "--hook")
        self.assertEqual(rc, 2)
        self.assertNotIn("Traceback", err)


class Title(unittest.TestCase):
    def test_duplicate_and_no_number(self):
        rc, out, _ = run(os.path.join(SK, "yt-package", "title.py"), "--title", "I Quit My Job",
                         "--thumb", "QUIT", "--json")
        kinds = [k for k, _ in json.loads(out)[0]["issues"]]
        self.assertIn("duplicate", kinds)
        self.assertIn("no-number", kinds)

    def test_long_title_flags_length(self):
        rc, out, _ = run(os.path.join(SK, "yt-package", "title.py"), "--title", "x" * 70, "--json")
        self.assertIn("length", [k for k, _ in json.loads(out)[0]["issues"]])


class Swipe(Base):
    def test_multiple_of_own_median_and_thin_channels_skipped(self):
        vids = [{"channel": "A", "title": f"v{i}", "views": v} for i, v in enumerate([100, 100, 100, 100, 900])]
        vids.append({"channel": "B", "title": "solo", "views": 10 ** 7})
        p = self.write("c.json", json.dumps(vids))
        rc, out, _ = run(os.path.join(SK, "yt-viral", "swipe.py"), p, "--json")
        d = json.loads(out)
        self.assertEqual(d["outliers"][0]["multiple"], 9.0)
        self.assertEqual(d["skipped_thin_channels"], [["B", 1]])


class Packaging(unittest.TestCase):
    def same(self, a, b):
        self.assertEqual(open(os.path.join(SK, a), "rb").read(), open(os.path.join(SK, b), "rb").read(),
                         f"{b} drifted from {a}; run tests/sync.sh")

    def test_vendored_copies_in_sync(self):
        for d in ("yt-chapters", "yt-retention"):
            self.same("yt-edit/transcript.py", f"{d}/transcript.py")
        self.same("yt-script/hooks.json", "yt-viral/hooks.json")

    def test_each_skill_runs_when_copied_alone(self):
        for skill, script, args in [("yt-chapters", "chapters.py", ["t.srt"]),
                                    ("yt-retention", "retention.py", ["r.csv", "--transcript", "t.srt"]),
                                    ("yt-viral", "swipe.py", ["c.json"]),
                                    ("yt-edit", "deadair.py", ["t.srt"]),
                                    ("yt-script", "hookscore.py", ["--hook", "You lose 40% fast, why?"])]:
            with tempfile.TemporaryDirectory() as d:
                dest = os.path.join(d, skill)
                shutil.copytree(os.path.join(SK, skill), dest)
                open(os.path.join(dest, "t.srt"), "w").write(srt(CUES))
                open(os.path.join(dest, "r.csv"), "w").write(
                    retention_csv([(i * 10, 100 - i * 4 - (20 if i > 3 else 0)) for i in range(11)]))
                open(os.path.join(dest, "c.json"), "w").write(
                    json.dumps([{"channel": "A", "title": "t", "views": 5}] * 4))
                rc, out, err = run(os.path.join(dest, script), *args, cwd=dest)
                self.assertEqual(rc, 0, f"{skill}: {err}")


if __name__ == "__main__":
    unittest.main()

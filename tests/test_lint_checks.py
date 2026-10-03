"""One positive and one negative scene per lint check (in-process, fast)."""
from manim import (BLUE, DOWN, LEFT, RIGHT, UP, Arrow, FadeIn, Line, Rectangle, Scene,
                   Text, VGroup)

from ipmotion_lib import IPBlock, Theme
from ipmotion.lint.report import build_report
from ipmotion.lint.worker import run_scene

TH = Theme()


def lint(scene_cls, only=None):
    return build_report(run_scene(scene_cls), "<test>", only=only)


def hits(rep, check, severity="error"):
    return [i for i in rep["issues"] if i["check"] == check and i["severity"] == severity]


def txt(s, size=24, **kw):
    return Text(s, font="Consolas", font_size=size, **kw)


# ----------------------------------------------------------- text_overlap
class TextOverlapPos(Scene):
    def construct(self):
        a, b = txt("Hello"), txt("World").shift(RIGHT * 0.3 + DOWN * 0.05)
        self.add(a, b)


class TextOverlapNeg(Scene):
    def construct(self):
        self.add(txt("Hello"), txt("World").shift(DOWN * 1))


class TextThroughWire(Scene):
    def construct(self):
        self.add(txt("LABEL"), Line(LEFT * 2, RIGHT * 2))


class WireBesideText(Scene):
    def construct(self):
        self.add(txt("LABEL"), Line(LEFT * 2 + DOWN, RIGHT * 2 + DOWN))


class TextOnForeignBlock(Scene):
    def construct(self):
        blk = IPBlock("BLOCK", TH, width=3, height=1.5)
        self.add(blk, txt("stray").move_to(blk.get_center() + RIGHT * 0.9))


class TextOverflowsOwnBlock(Scene):
    def construct(self):
        blk = IPBlock("BLOCK", TH, width=2, height=1)
        blk.txt.scale(6)
        self.add(blk)


class OwnTitleIsFine(Scene):
    def construct(self):
        self.add(IPBlock("A long block title here", TH, width=2.5, height=1.2))


def test_text_overlap_text_vs_text():
    assert hits(lint(TextOverlapPos), "text_overlap")
    assert not hits(lint(TextOverlapNeg), "text_overlap")


def test_text_overlap_wire_through_text():
    r = hits(lint(TextThroughWire), "text_overlap")
    assert r and "runs through" in r[0]["detail"]
    assert not hits(lint(WireBesideText), "text_overlap")


def test_text_overlap_on_foreign_block_and_overflow():
    assert any("sits on top of block" in i["detail"] for i in hits(lint(TextOnForeignBlock), "text_overlap"))
    assert any("overflows its block" in i["detail"] for i in hits(lint(TextOverflowsOwnBlock), "text_overlap"))
    assert not hits(lint(OwnTitleIsFine), "text_overlap")


# ---------------------------------------------------------- text_occluded
class OccludedPos(Scene):
    def construct(self):
        self.add(txt("SECRET"), Rectangle(width=1.5, height=1, fill_color=BLUE, fill_opacity=1))


class OccludedBehind(Scene):                    # shape drawn BEFORE the text
    def construct(self):
        self.add(Rectangle(width=1.5, height=1, fill_color=BLUE, fill_opacity=1), txt("SECRET"))


class OccludedFaint(Scene):                     # later shape but fill opacity below threshold
    def construct(self):
        self.add(txt("SECRET"), Rectangle(width=1.5, height=1, fill_color=BLUE, fill_opacity=0.3))


class OccludedPartial(Scene):                   # covers roughly half of the text
    def construct(self):
        t = txt("SECRET")
        self.add(t, Rectangle(width=2, height=1, fill_color=BLUE, fill_opacity=1).move_to(t.get_right()))


class OccludedElsewhere(Scene):
    def construct(self):
        self.add(txt("SECRET"), Rectangle(width=1, height=1, fill_color=BLUE, fill_opacity=1).shift(DOWN * 2))


def test_text_occluded_cases():
    full = hits(lint(OccludedPos), "text_occluded")
    assert full and "100%" in full[0]["detail"]
    part = hits(lint(OccludedPartial), "text_occluded")
    assert part and "100%" not in part[0]["detail"]
    for neg in (OccludedBehind, OccludedFaint, OccludedElsewhere):
        assert not hits(lint(neg), "text_occluded"), neg.__name__


# ------------------------------------------------------ dangling_endpoint
def _two_blocks():
    a = IPBlock("A", TH, width=2, height=1.5).shift(LEFT * 4)
    b = IPBlock("B", TH, width=2, height=1.5).shift(RIGHT * 4)
    return a, b


class DanglingPos(Scene):
    def construct(self):
        a, b = _two_blocks()
        self.add(a, b, Arrow(a.get_right(), b.get_left() + LEFT * 2, buff=0))


class DanglingNeg(Scene):
    def construct(self):
        a, b = _two_blocks()
        self.add(a, b, Arrow(a.get_right(), b.get_left(), buff=0.1))


class DanglingInsideBlock(Scene):
    def construct(self):
        a, b = _two_blocks()
        self.add(a, b, Arrow(a.get_right(), b.get_center(), buff=0))


class WireHiddenUnderBlock(Scene):              # centre-to-centre line drawn before opaque blocks
    def construct(self):
        a, b = _two_blocks()
        self.add(Line(a.get_center(), b.get_center()), a, b)


class JunctionTee(Scene):
    def construct(self):
        a, b = _two_blocks()
        trunk = Line(a.get_right(), b.get_left())
        branch = Arrow(a.get_right() + RIGHT * 3 + DOWN * 2, a.get_right() + RIGHT * 3, buff=0)
        self.add(a, b, trunk, branch)           # branch starts in empty space but ends on the trunk


def test_dangling_endpoint_cases():
    pos = hits(lint(DanglingPos), "dangling_endpoint")
    assert len(pos) == 1 and "empty space" in pos[0]["detail"]
    assert not hits(lint(DanglingNeg), "dangling_endpoint")
    inside = hits(lint(DanglingInsideBlock), "dangling_endpoint")
    assert inside and "inside block" in inside[0]["detail"]
    assert not hits(lint(WireHiddenUnderBlock), "dangling_endpoint")
    tee = hits(lint(JunctionTee), "dangling_endpoint")
    assert len(tee) == 1 and "start of" in tee[0]["detail"]      # only the free end is flagged


# ----------------------------------------------------------- out_of_frame
class OofPartial(Scene):
    def construct(self):
        self.add(IPBlock("EDGE", TH, width=2, height=1).shift(RIGHT * 6.5))


class OofFullText(Scene):
    def construct(self):
        self.add(txt("GONE").shift(UP * 6))


class OofMargin(Scene):
    def construct(self):
        self.add(IPBlock("SNUG", TH, width=2, height=1).shift(RIGHT * 6.0))


class OofInside(Scene):
    def construct(self):
        self.add(IPBlock("OK", TH, width=2, height=1))


class OofContainer(Scene):
    def construct(self):
        self.add(Rectangle(width=30, height=2, fill_opacity=0.1), IPBlock("OK", TH, width=2, height=1))


def test_out_of_frame_cases():
    assert "beyond the frame" in hits(lint(OofPartial), "out_of_frame")[0]["detail"]
    assert "entirely outside" in hits(lint(OofFullText), "out_of_frame")[0]["detail"]
    snug = lint(OofMargin)
    assert not hits(snug, "out_of_frame") and hits(snug, "out_of_frame", "warning")
    assert not lint(OofInside)["issues"]
    cont = lint(OofContainer)
    assert not hits(cont, "out_of_frame") and hits(cont, "out_of_frame", "warning")   # full-bleed bar: warning only


# ------------------------------------------------------------ min_spacing
class SpacingOverlap(Scene):
    def construct(self):
        a = IPBlock("A", TH, width=2, height=1)
        b = IPBlock("B", TH, width=2, height=1).shift(RIGHT * 1.2)
        self.add(a, b)


class SpacingTight(Scene):
    def construct(self):
        a = IPBlock("A", TH, width=2, height=1)
        b = IPBlock("B", TH, width=2, height=1).shift(RIGHT * 2.05)
        self.add(a, b)


class SpacingFine(Scene):
    def construct(self):
        self.add(IPBlock("A", TH, width=2, height=1), IPBlock("B", TH, width=2, height=1).shift(RIGHT * 3))


class SpacingNested(Scene):
    def construct(self):
        self.add(IPBlock("OUTER", TH, width=5, height=3), IPBlock("in", TH, width=1, height=0.6))


class SpacingStraddle(Scene):
    def construct(self):
        dom = Rectangle(width=6, height=3, fill_opacity=0.05).shift(LEFT * 3)
        inside = IPBlock("IN", TH, width=1.5, height=0.8).move_to(dom.get_center())
        straddler = IPBlock("OUT", TH, width=1.5, height=0.8).move_to(dom.get_right())
        self.add(dom, inside, straddler)


def test_min_spacing_cases():
    assert "overlap" in hits(lint(SpacingOverlap), "min_spacing")[0]["detail"]
    tight = lint(SpacingTight)
    assert not hits(tight, "min_spacing") and hits(tight, "min_spacing", "warning")
    assert not lint(SpacingFine)["issues"]
    assert not hits(lint(SpacingNested), "min_spacing")
    assert "straddles" in hits(lint(SpacingStraddle), "min_spacing")[0]["detail"]


# ---------------------------------------------------------- min_text_size
class SizeTiny(Scene):
    def construct(self):
        self.add(txt("tiny", 6))


class SizeSmall(Scene):
    def construct(self):
        self.add(txt("small", 9))


class SizeFine(Scene):
    def construct(self):
        self.add(txt("fine", 14))


class SizeScaledDown(Scene):                    # size is judged AFTER scaling
    def construct(self):
        g = VGroup(txt("scaled", 24)).scale(0.2)
        self.add(g)


def test_min_text_size_cases():
    assert hits(lint(SizeTiny), "min_text_size")
    small = lint(SizeSmall)
    assert not hits(small, "min_text_size") and hits(small, "min_text_size", "warning")
    assert not lint(SizeFine)["issues"]
    assert hits(lint(SizeScaledDown), "min_text_size")


# --------------------------------------------------- lint_ignore / harness
class IgnoredOverlap(Scene):
    def construct(self):
        a, b = txt("Hello"), txt("World").shift(RIGHT * 0.3)
        a.lint_ignore = ["text_overlap"]
        self.add(a, b)


class IgnoreAll(Scene):
    def construct(self):
        t = txt("tiny", 6)
        t.lint_ignore = "all"
        self.add(t)


class Crashes(Scene):
    def construct(self):
        self.add(txt("before"))
        self.wait(1)
        raise ValueError("boom")


class Timeline(Scene):
    def construct(self):
        t = txt("move me")
        self.play(FadeIn(t), run_time=2)
        self.wait(1.5)
        self.play(t.animate.shift(RIGHT * 20), run_time=1)


def test_lint_ignore_reports_info_not_error():
    rep = lint(IgnoredOverlap)
    assert rep["ok"] and rep["summary"]["error"] == 0 and rep["summary"]["info"] == 1
    info = [i for i in rep["issues"] if i["severity"] == "info"][0]
    assert info["check"] == "text_overlap" and info["ignored"] and info["ignored_by"]
    assert lint(IgnoreAll)["ok"]


def test_runtime_error_is_reported_with_partial_snapshots():
    rep = lint(Crashes)
    assert not rep["ok"] and hits(rep, "runtime_error")
    assert "boom" in hits(rep, "runtime_error")[0]["detail"]
    assert rep["snapshots"] >= 1                      # the wait() before the crash was captured


def test_snapshots_follow_play_and_wait_with_times_and_lines():
    res = run_scene(Timeline)
    calls = [(s["call"], s["t"]) for s in res["snapshots"]]
    assert calls == [("play", 2.0), ("wait", 3.5), ("play", 4.5), ("end", 4.5)]
    assert all(s["line"] > 0 for s in res["snapshots"])
    rep = build_report(res, "<test>")
    oof = hits(rep, "out_of_frame")
    assert oof and oof[0]["first_t"] == 4.5 and oof[0]["count"] == 2   # only after the last play(); seen by 2 snapshots

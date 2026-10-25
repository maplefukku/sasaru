import os
import unittest

from helpers import FAKE_KEY, AdapterCase, FakeTransport

from _lib.gates import looks_like_talking_head


class SpendGate(AdapterCase):
    def setUp(self):
        super().setUp()
        os.environ["XAI_API_KEY"] = FAKE_KEY

    def _run(self, *argv):
        fake = FakeTransport()
        code, out, err = self.call("t2v", "run", "--request", str(self.req("t2v")), "--out", str(self.out),
                                   *argv, transport=fake)
        self.assertEqual(fake.calls, [], "a refused run must not touch the network")
        self.assertFalse(self.out.exists())
        return code, err

    def test_run_without_yes_or_cap_is_refused(self):
        code, err = self._run()
        self.assertEqual(code, 3)
        self.assertIn("--yes", err)
        self.assertIn("--cap-usd", err)

    def test_run_with_yes_only_is_refused(self):
        code, err = self._run("--yes")
        self.assertEqual(code, 3)
        self.assertIn("--cap-usd", err)

    def test_run_with_cap_only_is_refused(self):
        code, err = self._run("--cap-usd", "10")
        self.assertEqual(code, 3)
        self.assertIn("--yes", err)

    def test_cap_below_quote_max_is_refused(self):
        code, err = self._run("--yes", "--cap-usd", "0.149")
        self.assertEqual(code, 3)
        self.assertIn("0.1500", err)

    def test_non_positive_cap_is_refused(self):
        code, _ = self._run("--yes", "--cap-usd", "0")
        self.assertEqual(code, 3)
        code, _ = self._run("--yes", "--cap-usd", "nan")
        self.assertEqual(code, 3)

    def test_zero_quote_is_never_sent(self):
        from _lib.errors import Refused
        from _lib.gates import check_spend
        from _lib.quote import Quote
        with self.assertRaises(Refused):
            check_spend(Quote(0, 0, "2026-10-25", "x"), yes=True, cap_usd=1.0)

    def test_missing_key_stops_before_sending(self):
        del os.environ["XAI_API_KEY"]
        code, err = self._run("--yes", "--cap-usd", "1")
        self.assertEqual(code, 2)
        self.assertIn("XAI_API_KEY", err)


class PeopleGate(AdapterCase):
    TALKING = [
        "a woman talking to the camera in her kitchen",
        "young man speaks directly into the lens",
        "lip-sync to the voiceover",
        "talking head explainer",
        "カメラに向かって話す女性",
        "視聴者に語りかける男性",
        "人が喋っているところ",
        "自撮りで一人語り",
        "she looks into the lens and talks about the product",
        "direct-to-camera UGC testimonial",
        "talking-to-the-camera product review",
        "カメラ目線で話す女性",
        "こちらを見て話す",
        "talking\u200b to the camera",
        "ＴＡＬＫＩＮＧ ＨＥＡＤ",
    ]
    NOT_TALKING = [
        "rain on a window, slow push in",
        "hands writing in a paper notebook, top-down",
        "ノートを開く手元、机の上、朝の光",
        "抽象的なグラデーションの背景がゆっくり動く",
        "a mascot bear waves at a desk",
        "close-up of a coffee cup steam",
    ]

    def test_talking_head_phrases(self):
        for p in self.TALKING:
            self.assertTrue(looks_like_talking_head(p), p)
        for p in self.NOT_TALKING:
            self.assertFalse(looks_like_talking_head(p), p)

    def test_talking_prompt_is_refused_by_default(self):
        for need in ("t2v", "i2v", "v2v"):
            inputs = [self.file("x.mp4" if need == "v2v" else "x.png")] if need != "t2v" else []
            req = self.req(need, prompt="カメラに向かって話す女性", inputs=inputs)
            code, _, err = self.call(need, "quote", "--request", str(req))
            self.assertEqual(code, 3, need)
            self.assertIn("lipsync", err)

    def test_talking_head_flag_is_refused_by_default(self):
        code, _, _ = self.call("t2v", "quote", "--request", str(self.req("t2v", talkingHead=True)))
        self.assertEqual(code, 3)

    def test_talking_head_passes_only_when_route_needs_say_so(self):
        req = self.req("t2v", prompt="a woman talking to the camera", routeNeeds=["t2v"])
        self.assertEqual(self.call("t2v", "quote", "--request", str(req))[0], 3)
        req = self.req("t2v", prompt="a woman talking to the camera", routeNeeds=["t2v", "lipsync"])
        self.assertEqual(self.call("t2v", "quote", "--request", str(req))[0], 0)

    def test_r2v_without_reference_kind_is_treated_as_face(self):
        req = self.req("r2v", inputs=[self.file("ref.png")])
        code, _, err = self.call("r2v", "quote", "--request", str(req))
        self.assertEqual(code, 3)
        self.assertIn("referenceKind", err)

    def test_face_r2v_passes_only_with_r2v_in_route_needs(self):
        req = self.req("r2v", inputs=[self.file("ref.png")], referenceKind="face", routeNeeds=["lipsync"])
        self.assertEqual(self.call("r2v", "quote", "--request", str(req))[0], 3)
        req = self.req("r2v", inputs=[self.file("ref.png")], referenceKind="face", routeNeeds=["r2v"])
        self.assertEqual(self.call("r2v", "quote", "--request", str(req))[0], 0)

    def test_declared_face_on_other_needs_is_refused(self):
        req = self.req("i2v", inputs=[self.file("me.png")], referenceKind="face")
        self.assertEqual(self.call("i2v", "quote", "--request", str(req))[0], 3)

    def test_non_face_r2v_is_allowed(self):
        for kind in ("character", "product", "object", "scene", "style"):
            req = self.req("r2v", inputs=[self.file("ref.png")], referenceKind=kind)
            self.assertEqual(self.call("r2v", "quote", "--request", str(req))[0], 0, kind)

    def test_tts_text_may_mention_speaking(self):
        req = self.req("tts", prompt="喋るのが苦手でも、ノートなら続けられる。")
        self.assertEqual(self.call("tts", "quote", "--request", str(req))[0], 0)

    def test_unknown_route_need_is_input_error(self):
        req = self.req("t2v", routeNeeds=["face"])
        self.assertEqual(self.call("t2v", "quote", "--request", str(req))[0], 2)


class ReferenceReelGate(AdapterCase):
    def test_inputs_from_sasaru_work_are_refused(self):
        clip = self.file("proj/sasaru/work/ref-01/source.mp4")
        code, _, err = self.call("v2v", "quote", "--request", str(self.req("v2v", inputs=[clip])))
        self.assertEqual(code, 3)
        self.assertIn("sasaru/work", err)

    def test_symlink_into_sasaru_work_is_refused(self):
        target = self.file("outside/reel.png")
        link = self.tmp / "proj/sasaru/work/reel.png"
        link.parent.mkdir(parents=True)
        link.symlink_to(target)
        code, _, _ = self.call("i2v", "quote", "--request", str(self.req("i2v", inputs=[str(link)])))
        self.assertEqual(code, 3)

    def test_symlink_out_of_sasaru_work_is_refused(self):
        target = self.file("proj/sasaru/work/ref/reel.png")
        link = self.tmp / "innocent.png"
        link.symlink_to(target)
        code, _, _ = self.call("i2v", "quote", "--request", str(self.req("i2v", inputs=[str(link)])))
        self.assertEqual(code, 3)

    def test_sasaru_home_work_that_is_a_symlink_is_refused(self):
        reels = self.tmp / "reels"
        reels.mkdir()
        frame = self.file("reels/a.png")
        (self.tmp / "lib").mkdir()
        (self.tmp / "lib/work").symlink_to(reels)
        os.environ["SASARU_HOME"] = str(self.tmp / "lib")
        for p in (frame, str(self.tmp / "lib/work/a.png")):
            code, _, _ = self.call("i2v", "quote", "--request", str(self.req("i2v", inputs=[p])))
            self.assertEqual(code, 3, p)

    def test_inputs_from_sasaru_home_work_are_refused(self):
        os.environ["SASARU_HOME"] = str(self.tmp / "lib")
        frame = self.file("lib/work/ref-01/keyframe.png")
        code, _, _ = self.call("i2v", "quote", "--request", str(self.req("i2v", inputs=[frame])))
        self.assertEqual(code, 3)


if __name__ == "__main__":
    unittest.main()

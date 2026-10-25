import os
import shutil
import unittest
from datetime import date
from unittest import mock

from helpers import FAKE_KEY, AdapterCase, FakeTransport


class QuoteShape(AdapterCase):
    def test_quote_is_the_make_contract_and_needs_no_key_or_network(self):
        q = self.quote("t2v", self.req("t2v", durationSec=5.5))
        self.assertEqual(set(q), {"usdMin", "usdMax", "asOf", "basis"})
        self.assertEqual(q["asOf"], "2026-10-25")
        self.assertAlmostEqual(q["usdMax"], 0.03 * 6)
        self.assertIn("docs.x.ai", q["basis"])

    def test_need_with_underscore_matches_script(self):
        q = self.quote("image-gen", self.req("image_gen", durationSec=None))
        self.assertAlmostEqual(q["usdMin"], 0.0336)

    def test_wrong_need_for_script_is_input_error(self):
        code, _, err = self.call("t2v", "quote", "--request", str(self.req("i2v")))
        self.assertEqual(code, 2)
        self.assertIn("need", err)

    def test_unknown_provider_lists_choices(self):
        code, _, err = self.call("t2v", "quote", "--request", str(self.req("t2v")), "--provider", "openai-sora-2")
        self.assertEqual(code, 2)
        self.assertIn("runway-gen4.5", err)


class VideoQuotes(AdapterCase):
    def test_runway_gen45_bills_whole_seconds(self):
        q = self.quote("t2v", self.req("t2v", durationSec=5.2, provider="runway-gen4.5"))
        self.assertAlmostEqual(q["usdMax"], 0.12 * 6)

    def test_runway_gen45_rejects_over_ten_seconds(self):
        code, _, err = self.call("t2v", "quote", "--request", str(self.req("t2v", durationSec=11, provider="runway-gen4.5")))
        self.assertEqual(code, 2)
        self.assertIn("10", err)

    def test_runway_gen45_t2v_has_no_square(self):
        code, _, _ = self.call("t2v", "quote", "--request", str(self.req("t2v", aspect="1:1", provider="runway-gen4.5")))
        self.assertEqual(code, 2)

    def test_xai_i2v_adds_input_image(self):
        q = self.quote("i2v", self.req("i2v", inputs=[self.file("first.png")]))
        self.assertAlmostEqual(q["usdMax"], 0.03 * 5 + 0.01)

    def test_i2v_needs_exactly_one_image(self):
        code, _, _ = self.call("i2v", "quote", "--request", str(self.req("i2v")))
        self.assertEqual(code, 2)
        code, _, _ = self.call("i2v", "quote", "--request", str(self.req("i2v", inputs=[self.file("a.mp4")])))
        self.assertEqual(code, 2)

    def test_xai_r2v_product_refs(self):
        refs = [self.file(f"ref{i}.png") for i in range(3)]
        q = self.quote("r2v", self.req("r2v", inputs=refs, referenceKind="product"))
        self.assertAlmostEqual(q["usdMax"], 0.14 * 5 + 0.03)

    def test_xai_r2v_is_capped_at_720p(self):
        req = self.req("r2v", inputs=[self.file("r.png")], referenceKind="product", resolution="1080p")
        code, _, _ = self.call("r2v", "quote", "--request", str(req))
        self.assertEqual(code, 2)

    def test_missing_input_file_is_input_error(self):
        code, _, err = self.call("i2v", "quote", "--request", str(self.req("i2v", inputs=["nope.png"])))
        self.assertEqual(code, 2)
        self.assertIn("nope.png", err)


class V2VQuotes(AdapterCase):
    def test_aleph2_uses_probed_input_length(self):
        with mock.patch("_lib.providers.runway.probe_duration", return_value=4.2):
            q = self.quote("v2v", self.req("v2v", inputs=[self.file("clip.mp4")]))
        self.assertAlmostEqual(q["usdMin"], 0.28 * 5)
        self.assertAlmostEqual(q["usdMax"], 0.28 * 5)

    def test_aleph2_minimum_charge(self):
        with mock.patch("_lib.providers.runway.probe_duration", return_value=2.0):
            q = self.quote("v2v", self.req("v2v", inputs=[self.file("clip.mp4")]))
        self.assertAlmostEqual(q["usdMax"], 0.56)

    def test_aleph2_without_ffprobe_quotes_the_worst_case(self):
        with mock.patch("_lib.providers.runway.probe_duration", return_value=None):
            q = self.quote("v2v", self.req("v2v", durationSec=4, inputs=[self.file("clip.mp4")]))
        self.assertAlmostEqual(q["usdMax"], 0.28 * 30)
        self.assertLess(q["usdMin"], q["usdMax"])

    def test_aleph2_without_ffprobe_refuses_to_send(self):
        os.environ["RUNWAYML_API_SECRET"] = FAKE_KEY
        fake = FakeTransport()
        with mock.patch("_lib.providers.runway.probe_duration", return_value=None):
            code, _, err = self.run_paid("v2v", self.req("v2v", inputs=[self.file("clip.mp4")]), fake, "20")
        self.assertEqual(code, 2, err)
        self.assertIn("ffprobe", err)
        self.assertEqual(fake.calls, [])

    def test_aleph2_rejects_short_input(self):
        with mock.patch("_lib.providers.runway.probe_duration", return_value=1.0):
            code, _, _ = self.call("v2v", "quote", "--request", str(self.req("v2v", inputs=[self.file("c.mp4")])))
        self.assertEqual(code, 2)

    def test_xai_edit_bills_input_and_output(self):
        with mock.patch("_lib.providers.xai.probe_duration", return_value=6.0):
            q = self.quote("v2v", self.req("v2v", inputs=[self.file("c.mp4")], provider="xai-grok-imagine-video"))
        self.assertAlmostEqual(q["usdMax"], (0.07 + 0.01) * 6)

    @unittest.skipUnless(shutil.which("ffprobe"), "needs ffprobe")
    def test_unreadable_or_zero_length_video_is_input_error(self):
        clip = self.file("zero.mp4", b"not a video")
        for provider in ("runway-aleph2", "xai-grok-imagine-video"):
            code, _, _ = self.call("v2v", "quote", "--request", str(self.req("v2v", inputs=[clip], provider=provider)))
            self.assertEqual(code, 2, provider)

    def test_xai_edit_bills_at_least_one_second(self):
        with mock.patch("_lib.providers.xai.probe_duration", return_value=0.6):
            q = self.quote("v2v", self.req("v2v", inputs=[self.file("c.mp4")], provider="xai-grok-imagine-video"))
        self.assertAlmostEqual(q["usdMax"], 0.08)

    def test_xai_edit_source_limit(self):
        with mock.patch("_lib.providers.xai.probe_duration", return_value=9.0):
            code, _, _ = self.call("v2v", "quote", "--request",
                                   str(self.req("v2v", inputs=[self.file("c.mp4")], provider="xai-grok-imagine-video")))
        self.assertEqual(code, 2)


class ImageQuotes(AdapterCase):
    def test_nano_banana_4k_quotes_both_documented_token_counts(self):
        q = self.quote("image-gen", self.req("image-gen", resolution="4k", prompt="x"))
        self.assertAlmostEqual(q["usdMin"], 2520 * 30 / 1e6)
        self.assertGreater(q["usdMax"], 3780 * 30 / 1e6)

    def test_nano_banana_count_multiplies(self):
        q = self.quote("image-gen", self.req("image-gen", count=3))
        self.assertAlmostEqual(q["usdMin"], 0.0336 * 3)

    def test_flux_klein_and_flux(self):
        self.assertAlmostEqual(self.quote("image-gen", self.req("image-gen", provider="bfl-flux-3-image-klein"))["usdMax"], 0.009)
        self.assertAlmostEqual(self.quote("image-gen", self.req("image-gen", provider="bfl-flux-3-image", resolution="2k"))["usdMax"], 0.10)

    def test_flux_refuses_reference_images(self):
        req = self.req("image-gen", provider="bfl-flux-3-image", inputs=[self.file("r.png")])
        code, _, _ = self.call("image-gen", "quote", "--request", str(req))
        self.assertEqual(code, 2)

    def test_grok_image_quality_tiers(self):
        q = self.quote("image-gen", self.req("image-gen", provider="xai-grok-imagine-image-2.0", resolution="2k", quality="medium"))
        self.assertAlmostEqual(q["usdMax"], 0.08)


class TTSQuotes(AdapterCase):
    def test_eleven_v4_per_character(self):
        q = self.quote("tts", self.req("tts", prompt="あ" * 1000))
        self.assertAlmostEqual(q["usdMax"], 0.08)
        q = self.quote("tts", self.req("tts", prompt="あ" * 1000, provider="elevenlabs-eleven-v4-turbo"))
        self.assertAlmostEqual(q["usdMax"], 0.04)

    def test_eleven_rejects_over_limit(self):
        code, _, _ = self.call("tts", "quote", "--request", str(self.req("tts", prompt="a" * 10001)))
        self.assertEqual(code, 2)

    def test_gemini_tts_max_is_the_output_cap(self):
        q = self.quote("tts", self.req("tts", provider="google-gemini-3.8-flash-tts"))
        self.assertAlmostEqual(q["usdMax"], 16384 * 9 / 1e6 + 8192 * 0.5 / 1e6)
        self.assertAlmostEqual(q["usdMin"], 5 * 0.8 * 25 * 9 / 1e6)

    def test_gemini_tts_price_doubles_in_2027(self):
        with mock.patch("_lib.providers.google._today", return_value=date(2027, 1, 1)):
            q = self.quote("tts", self.req("tts", provider="google-gemini-3.8-flash-lite-tts"))
        self.assertAlmostEqual(q["usdMax"], 16384 * 12 / 1e6 + 8192 * 1.0 / 1e6)


if __name__ == "__main__":
    unittest.main()

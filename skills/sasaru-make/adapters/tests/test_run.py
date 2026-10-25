import base64
import json
import os
import unittest
import wave
from pathlib import Path
from unittest import mock

from helpers import FAKE_KEY, AdapterCase, FakeTransport, resp

VIDEO = b"\x00\x00\x00\x18ftypmp42 fake video"


class XaiRun(AdapterCase):
    def setUp(self):
        super().setUp()
        os.environ["XAI_API_KEY"] = FAKE_KEY

    def test_t2v_submit_poll_download(self):
        fake = FakeTransport(
            ("POST", "https://api.x.ai/v1/videos/generations", resp(200, {"request_id": "req-1"})),
            ("GET", "https://api.x.ai/v1/videos/req-1", resp(200, {"status": "pending"})),
            ("GET", "https://api.x.ai/v1/videos/req-1",
             resp(200, {"status": "done", "video": {"url": "https://vidgen.x.ai/out/req-1.mp4"}})),
            ("GET", "https://vidgen.x.ai/out/req-1.mp4", resp(200, VIDEO, {"Content-Type": "video/mp4"})),
        )
        code, out, err = self.run_paid("t2v", self.req("t2v", durationSec=4.5), fake, "0.15")
        self.assertEqual(code, 0, err)
        result = json.loads(out)
        self.assertEqual(result["provider"], "xai-grok-imagine-video-1.5-lite")
        self.assertAlmostEqual(result["usd"], 0.15)
        [path] = result["files"]
        self.assertEqual(Path(path).read_bytes(), VIDEO)
        self.assertEqual(Path(path).name, "cut-01-b2-xai-grok-imagine-video-1.5-lite.mp4")

        body = fake.json_body(0)
        self.assertEqual(body, {"model": "grok-imagine-video-1.5-lite", "prompt": "rain on a window, slow push in",
                                "duration": 5, "resolution": "720p", "aspect_ratio": "9:16"})
        self.assertEqual(fake.calls[0]["headers"]["Authorization"], f"Bearer {FAKE_KEY}")
        self.assertNotIn("Authorization", fake.calls[3]["headers"], "key must not go to the download host")
        self.assert_no_key_leak(out, err)

    def test_i2v_sends_image_as_data_uri(self):
        fake = FakeTransport(
            ("POST", "https://api.x.ai/v1/videos/generations", resp(200, {"request_id": "r"})),
            ("GET", "https://api.x.ai/v1/videos/r", resp(200, {"video": {"url": "https://vidgen.x.ai/r.mp4"}})),
            ("GET", "https://vidgen.x.ai/r.mp4", resp(200, VIDEO)),
        )
        req = self.req("i2v", inputs=[self.file("first.png", b"PNGDATA")])
        code, _, err = self.run_paid("i2v", req, fake, "1")
        self.assertEqual(code, 0, err)
        body = fake.json_body(0)
        self.assertEqual(body["image"]["url"], "data:image/png;base64," + base64.b64encode(b"PNGDATA").decode())
        self.assertNotIn("aspect_ratio", body)

    def test_r2v_sends_reference_images(self):
        fake = FakeTransport(
            ("POST", "https://api.x.ai/v1/videos/generations", resp(200, {"request_id": "r"})),
            ("GET", "https://api.x.ai/v1/videos/r", resp(200, {"status": "done", "video": {"url": "https://vidgen.x.ai/r.mp4"}})),
            ("GET", "https://vidgen.x.ai/r.mp4", resp(200, VIDEO)),
        )
        req = self.req("r2v", inputs=[self.file("a.png"), self.file("b.jpg")], referenceKind="character")
        code, _, err = self.run_paid("r2v", req, fake, "1")
        self.assertEqual(code, 0, err)
        body = fake.json_body(0)
        self.assertEqual(body["model"], "grok-imagine-video-1.5")
        self.assertEqual(len(body["reference_images"]), 2)

    def test_v2v_edit_endpoint(self):
        fake = FakeTransport(
            ("POST", "https://api.x.ai/v1/videos/edits", resp(200, {"request_id": "e"})),
            ("GET", "https://api.x.ai/v1/videos/e", resp(200, {"status": "done", "video": {"url": "https://vidgen.x.ai/e.mp4"}})),
            ("GET", "https://vidgen.x.ai/e.mp4", resp(200, VIDEO)),
        )
        with mock.patch("_lib.providers.xai.probe_duration", return_value=3.0):
            req = self.req("v2v", inputs=[self.file("own.mp4", VIDEO)], provider="xai-grok-imagine-video",
                           prompt="turn into a pencil sketch")
            code, out, err = self.run_paid("v2v", req, fake, "1")
        self.assertEqual(code, 0, err)
        self.assertTrue(fake.json_body(0)["video"]["url"].startswith("data:video/mp4;base64,"))
        self.assertAlmostEqual(json.loads(out)["usd"], 0.24)

    def test_failed_job_is_provider_error(self):
        fake = FakeTransport(
            ("POST", "https://api.x.ai/v1/videos/generations", resp(200, {"request_id": "x"})),
            ("GET", "https://api.x.ai/v1/videos/x", resp(200, {"status": "failed", "error": "moderated"})),
        )
        code, _, err = self.run_paid("t2v", self.req("t2v"), fake, "1")
        self.assertEqual(code, 4)
        self.assertIn("failed", err)

    def test_poll_timeout(self):
        t = iter(range(0, 10_000, 100))
        fake = FakeTransport(
            ("POST", "https://api.x.ai/v1/videos/generations", resp(200, {"request_id": "x"})),
            *[("GET", "https://api.x.ai/v1/videos/x", resp(200, {"status": "pending"}))] * 20,
        )
        code, _, err = self.run_paid("t2v", self.req("t2v"), fake, "1", "--timeout-sec", "250",
                                     clock=lambda: next(t))
        self.assertEqual(code, 4)
        self.assertIn("250", err)

    def test_http_error_body_is_redacted(self):
        fake = FakeTransport(
            ("POST", "https://api.x.ai/v1/videos/generations",
             resp(401, {"error": f"invalid key {FAKE_KEY}"})),
        )
        code, out, err = self.run_paid("t2v", self.req("t2v"), fake, "1")
        self.assertEqual(code, 4)
        self.assertIn("401", err)
        self.assertIn("***", err)
        self.assert_no_key_leak(out, err)

    def test_lost_submit_reply_is_not_retried(self):
        fake = FakeTransport(("POST", "https://api.x.ai/v1/videos/generations", ConnectionResetError("reset")))
        code, _, err = self.run_paid("t2v", self.req("t2v"), fake, "1")
        self.assertEqual(code, 4)
        self.assertIn("再送しません", err)
        self.assertEqual(len(fake.calls), 1)

    def test_grok_image_b64(self):
        fake = FakeTransport(
            ("POST", "https://api.x.ai/v1/images/generations",
             resp(200, {"data": [{"b64_json": base64.b64encode(b"JPG1").decode()},
                                 {"b64_json": base64.b64encode(b"JPG2").decode()}]})),
        )
        req = self.req("image-gen", provider="xai-grok-imagine-image-2.0", count=2)
        code, out, err = self.run_paid("image-gen", req, fake, "1")
        self.assertEqual(code, 0, err)
        files = json.loads(out)["files"]
        self.assertEqual([Path(f).read_bytes() for f in files], [b"JPG1", b"JPG2"])
        self.assertEqual(fake.json_body(0)["n"], 2)


class RunwayRun(AdapterCase):
    def setUp(self):
        super().setUp()
        os.environ["RUNWAYML_API_SECRET"] = FAKE_KEY

    def test_i2v_task_flow(self):
        fake = FakeTransport(
            ("POST", "https://api.dev.runwayml.com/v1/image_to_video", resp(200, {"id": "task-9"})),
            ("GET", "https://api.dev.runwayml.com/v1/tasks/task-9", resp(200, {"status": "RUNNING"})),
            ("GET", "https://api.dev.runwayml.com/v1/tasks/task-9",
             resp(200, {"status": "SUCCEEDED", "output": ["https://dnznrvs05pmza.cloudfront.net/o.mp4"]})),
            ("GET", "https://dnznrvs05pmza.cloudfront.net/o.mp4", resp(200, VIDEO, {"Content-Type": "video/mp4"})),
        )
        req = self.req("i2v", provider="runway-gen4.5", inputs=[self.file("f.jpg", b"JPG")], durationSec=8)
        code, out, err = self.run_paid("i2v", req, fake, "0.96")
        self.assertEqual(code, 0, err)
        body = fake.json_body(0)
        self.assertEqual(body["model"], "gen4.5")
        self.assertEqual(body["ratio"], "720:1280")
        self.assertEqual(body["duration"], 8)
        self.assertEqual(body["promptImage"][0]["position"], "first")
        self.assertTrue(body["promptImage"][0]["uri"].startswith("data:image/jpeg;base64,"))
        h = fake.calls[0]["headers"]
        self.assertEqual(h["X-Runway-Version"], "2024-11-06")
        self.assertEqual(h["Authorization"], f"Bearer {FAKE_KEY}")
        self.assertNotIn("Authorization", fake.calls[3]["headers"])
        self.assert_no_key_leak(out, err)

    def test_aleph2_v2v(self):
        fake = FakeTransport(
            ("POST", "https://api.dev.runwayml.com/v1/video_to_video", resp(200, {"id": "t"})),
            ("GET", "https://api.dev.runwayml.com/v1/tasks/t", resp(200, {"status": "SUCCEEDED", "output": ["https://cdn.example/o.mp4"]})),
            ("GET", "https://cdn.example/o.mp4", resp(200, VIDEO)),
        )
        with mock.patch("_lib.providers.runway.probe_duration", return_value=5.0):
            req = self.req("v2v", inputs=[self.file("own.mp4", VIDEO)], prompt="watercolor style")
            code, out, err = self.run_paid("v2v", req, fake, "1.40")
        self.assertEqual(code, 0, err)
        self.assertEqual(fake.json_body(0)["model"], "aleph2")
        self.assertTrue(fake.json_body(0)["videoUri"].startswith("data:video/mp4;base64,"))

    def test_failed_task(self):
        fake = FakeTransport(
            ("POST", "https://api.dev.runwayml.com/v1/text_to_video", resp(200, {"id": "t"})),
            ("GET", "https://api.dev.runwayml.com/v1/tasks/t", resp(200, {"status": "FAILED", "failureCode": "SAFETY"})),
        )
        code, _, err = self.run_paid("t2v", self.req("t2v", provider="runway-gen4.5"), fake, "1")
        self.assertEqual(code, 4)
        self.assertIn("SAFETY", err)


class BflRun(AdapterCase):
    def setUp(self):
        super().setUp()
        os.environ["BFL_API_KEY"] = FAKE_KEY

    def test_flux_poll_and_download(self):
        fake = FakeTransport(
            ("POST", "https://api.bfl.ai/v1/flux-3-image-klein",
             resp(200, {"id": "j1", "polling_url": "https://api.eu.bfl.ai/v1/get_result?id=j1"})),
            ("GET", "https://api.eu.bfl.ai/v1/get_result?id=j1", resp(200, {"status": "Pending"})),
            ("GET", "https://api.eu.bfl.ai/v1/get_result?id=j1",
             resp(200, {"status": "Ready", "result": {"sample": "https://delivery-eu1.bfl.ai/s.jpeg"}})),
            ("GET", "https://delivery-eu1.bfl.ai/s.jpeg", resp(200, b"JPEG", {"Content-Type": "image/jpeg"})),
        )
        req = self.req("image-gen", provider="bfl-flux-3-image-klein")
        code, out, err = self.run_paid("image-gen", req, fake, "0.01")
        self.assertEqual(code, 0, err)
        self.assertEqual(fake.json_body(0), {"prompt": "rain on a window, slow push in", "aspect_ratio": "9:16", "resolution": "1k"})
        self.assertEqual(fake.calls[0]["headers"]["x-key"], FAKE_KEY)
        self.assertEqual(fake.calls[1]["headers"]["x-key"], FAKE_KEY)
        self.assertNotIn("x-key", fake.calls[3]["headers"])
        self.assertTrue(json.loads(out)["files"][0].endswith(".jpg"))

    def test_foreign_polling_host_is_rejected(self):
        fake = FakeTransport(
            ("POST", "https://api.bfl.ai/v1/flux-3-image", resp(200, {"id": "j", "polling_url": "https://evil.example/poll"})),
        )
        code, _, err = self.run_paid("image-gen", self.req("image-gen", provider="bfl-flux-3-image"), fake, "1")
        self.assertEqual(code, 4)
        self.assertEqual(len(fake.calls), 1)

    def test_moderated(self):
        fake = FakeTransport(
            ("POST", "https://api.bfl.ai/v1/flux-3-image", resp(200, {"id": "j", "polling_url": "https://api.bfl.ai/v1/get_result?id=j"})),
            ("GET", "https://api.bfl.ai/v1/get_result?id=j", resp(200, {"status": "Content Moderated"})),
        )
        code, _, err = self.run_paid("image-gen", self.req("image-gen", provider="bfl-flux-3-image"), fake, "1")
        self.assertEqual(code, 4)
        self.assertIn("Moderated", err)


class GeminiRun(AdapterCase):
    def setUp(self):
        super().setUp()
        os.environ["GEMINI_API_KEY"] = FAKE_KEY

    def test_nano_banana_inline_image(self):
        png = b"\x89PNG\r\n\x1a\nfake"
        fake = FakeTransport(
            ("POST", "https://generativelanguage.googleapis.com/v1beta/models/gemini-nano-banana-2.1:generateContent",
             resp(200, {"candidates": [{"content": {"parts": [
                 {"text": "here"}, {"inlineData": {"mimeType": "image/png", "data": base64.b64encode(png).decode()}}]}}]})),
        )
        req = self.req("image-gen", inputs=[self.file("ref.png", b"REF")])
        code, out, err = self.run_paid("image-gen", req, fake, "0.05")
        self.assertEqual(code, 0, err)
        self.assertEqual(Path(json.loads(out)["files"][0]).read_bytes(), png)
        body = fake.json_body(0)
        self.assertEqual(body["generationConfig"]["imageConfig"], {"aspectRatio": "9:16", "imageSize": "1K"})
        self.assertEqual(body["contents"][0]["parts"][1]["inlineData"]["data"], base64.b64encode(b"REF").decode())
        self.assertEqual(fake.calls[0]["headers"]["x-goog-api-key"], FAKE_KEY)
        self.assertNotIn(FAKE_KEY, fake.calls[0]["url"])

    def test_blocked_prompt(self):
        fake = FakeTransport(
            ("POST", "https://generativelanguage.googleapis.com/v1beta/models/gemini-nano-banana-2.1:generateContent",
             resp(200, {"promptFeedback": {"blockReason": "SAFETY"}})),
        )
        code, _, err = self.run_paid("image-gen", self.req("image-gen"), fake, "1")
        self.assertEqual(code, 4)
        self.assertIn("SAFETY", err)

    def test_tts_pcm_becomes_wav(self):
        pcm = b"\x00\x01" * 2400
        fake = FakeTransport(
            ("POST", "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash-tts:generateContent",
             resp(200, {"candidates": [{"content": {"parts": [
                 {"inlineData": {"mimeType": "audio/L16;codec=pcm;rate=24000", "data": base64.b64encode(pcm).decode()}}]}}]})),
        )
        req = self.req("tts", prompt="ノートを開くと、三つのコツが見えてくる。", provider="google-gemini-3.8-flash-tts", voice="Puck")
        code, out, err = self.run_paid("tts", req, fake, "0.2")
        self.assertEqual(code, 0, err)
        [path] = json.loads(out)["files"]
        with wave.open(path) as w:
            self.assertEqual((w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()), (24000, 1, 2, 2400))
        voice = fake.json_body(0)["generationConfig"]["speechConfig"]["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"]
        self.assertEqual(voice, "Puck")

    def test_tts_cap_must_cover_the_output_ceiling(self):
        req = self.req("tts", prompt="短い文。", provider="google-gemini-3.8-flash-tts")
        code, _, err = self.run_paid("tts", req, FakeTransport(), "0.01")
        self.assertEqual(code, 3)


class ElevenRun(AdapterCase):
    def setUp(self):
        super().setUp()
        os.environ["ELEVENLABS_API_KEY"] = FAKE_KEY

    def test_with_timestamps_writes_audio_and_alignment(self):
        alignment = {"characters": ["ノ", "ー"], "character_start_times_seconds": [0.0, 0.1],
                     "character_end_times_seconds": [0.1, 0.2]}
        fake = FakeTransport(
            ("POST", "https://api.elevenlabs.io/v1/text-to-speech/voice123/with-timestamps?output_format=mp3_44100_128",
             resp(200, {"audio_base64": base64.b64encode(b"ID3mp3").decode(), "alignment": alignment,
                        "normalized_alignment": alignment})),
        )
        req = self.req("tts", prompt="ノー", voice="voice123", language="ja")
        code, out, err = self.run_paid("tts", req, fake, "0.01")
        self.assertEqual(code, 0, err)
        audio, timing = json.loads(out)["files"]
        self.assertEqual(Path(audio).read_bytes(), b"ID3mp3")
        self.assertTrue(timing.endswith(".alignment.json"))
        self.assertEqual(json.loads(Path(timing).read_text())["alignment"], alignment)
        self.assertEqual(fake.json_body(0), {"text": "ノー", "model_id": "eleven_v4", "apply_language_text_normalization": True})
        self.assertEqual(fake.calls[0]["headers"]["xi-api-key"], FAKE_KEY)
        self.assert_no_key_leak(out, err)

    def test_voice_from_env(self):
        os.environ["ELEVENLABS_VOICE_ID"] = "envVoice"
        fake = FakeTransport(
            ("POST", "https://api.elevenlabs.io/v1/text-to-speech/envVoice/with-timestamps",
             resp(200, {"audio_base64": base64.b64encode(b"x").decode()})),
        )
        code, out, err = self.run_paid("tts", self.req("tts", prompt="hi", provider="elevenlabs-eleven-v4-turbo"), fake, "1")
        self.assertEqual(code, 0, err)
        self.assertEqual(len(json.loads(out)["files"]), 1)

    def test_missing_voice_is_input_error_before_sending(self):
        fake = FakeTransport()
        code, _, err = self.run_paid("tts", self.req("tts", prompt="hi"), fake, "1")
        self.assertEqual(code, 2)
        self.assertEqual(fake.calls, [])

    def test_voice_id_cannot_inject_path(self):
        fake = FakeTransport()
        code, _, _ = self.run_paid("tts", self.req("tts", prompt="hi", voice="../../v1/user"), fake, "1")
        self.assertEqual(code, 2)
        self.assertEqual(fake.calls, [])


if __name__ == "__main__":
    unittest.main()

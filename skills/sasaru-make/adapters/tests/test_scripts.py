import json
import os
import subprocess
import sys
import unittest

from helpers import ADAPTERS, KEY_ENVS, AdapterCase

SCRIPTS = ("image_gen", "t2v", "i2v", "r2v", "v2v", "tts")


class Scripts(AdapterCase):
    def _clean_env(self):
        return {k: v for k, v in os.environ.items() if k not in KEY_ENVS}

    def test_each_script_has_a_pep723_header(self):
        for name in SCRIPTS:
            text = (ADAPTERS / f"{name}.py").read_text()
            self.assertTrue(text.startswith("#!/usr/bin/env -S uv run --script\n# /// script\n"), name)
            self.assertIn("# dependencies = []", text)

    def test_each_script_lists_providers_with_one_default(self):
        for name in SCRIPTS:
            out = subprocess.run([sys.executable, str(ADAPTERS / f"{name}.py"), "providers"],
                                 capture_output=True, text=True, env=self._clean_env(), check=True).stdout
            providers = json.loads(out)
            self.assertEqual(sum(p["default"] for p in providers), 1, name)

    def test_quote_through_the_script_entry(self):
        req = self.req("tts", prompt="あ" * 500)
        proc = subprocess.run([sys.executable, str(ADAPTERS / "tts.py"), "quote", "--request", str(req)],
                              capture_output=True, text=True, env=self._clean_env())
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertAlmostEqual(json.loads(proc.stdout)["usdMax"], 0.04)

    def test_run_through_the_script_entry_is_refused_without_flags(self):
        req = self.req("t2v")
        proc = subprocess.run([sys.executable, str(ADAPTERS / "t2v.py"), "run", "--request", str(req),
                               "--out", str(self.out)], capture_output=True, text=True, env=self._clean_env())
        self.assertEqual(proc.returncode, 3)
        self.assertEqual(proc.stdout, "")


if __name__ == "__main__":
    unittest.main()

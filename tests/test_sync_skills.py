"""Tests for nonighter/skills/sync-skills/scripts/sync_skills.py - the mod (NoNighter App) paths.

Stdlib only:  python -m unittest discover -s tests -v

Each test builds a throwaway plugin root (the repo's hooks.json and the shipped placeholder) and a data
dir, and runs the script as the skill does, with a manifest whose URLs are file:// links to zips built
here. Nothing touches the network or a real install.
"""
from __future__ import annotations

import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "nonighter"
SCRIPT = PLUGIN / "skills" / "sync-skills" / "scripts" / "sync_skills.py"
PLACEHOLDER = PLUGIN / "skills" / "sync-skills" / "mod-placeholder"


def zip_bytes(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, text in files.items():
            z.writestr(name, text)
    return buf.getvalue()


def mod_zip(version: str, marker: str = "ok") -> bytes:
    return zip_bytes({"hooks/register.tsx": f"// mod {marker}\n", "build.json": json.dumps({"version": version})})


class SyncCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sync-test-"))
        self.root = self.tmp / "plugin"
        (self.root / "hooks").mkdir(parents=True)
        shutil.copy(PLUGIN / "hooks" / "hooks.json", self.root / "hooks" / "hooks.json")
        shutil.copytree(PLACEHOLDER, self.root / "mods" / "noni-app")
        self.data = self.tmp / "data"
        self.data.mkdir()
        self.n = 0

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def entry(self, name: str, version: str, blob: bytes, **extra) -> dict:
        self.n += 1
        p = self.tmp / f"pkg-{self.n}.zip"
        p.write_bytes(blob)
        return {"name": name, "version": version, "sha256": hashlib.sha256(blob).hexdigest(),
                "size": len(blob), "url": p.as_uri(), **extra}

    def apply(self, *entries: dict) -> subprocess.CompletedProcess:
        m = self.tmp / f"manifest-{self.n}.json"
        m.write_text(json.dumps({"tenant": "test", "skills": list(entries)}), encoding="utf-8")
        return subprocess.run([sys.executable, "-I", str(SCRIPT), "--plugin-root", str(self.root), "--data-dir",
                               str(self.data), "apply", "--manifest", str(m)], capture_output=True, text=True)

    def receipt(self) -> dict:
        return json.loads((self.data / "sync-skills-receipt.json").read_text(encoding="utf-8"))["items"]

    @property
    def app(self) -> Path:
        return self.root / "mods" / "noni-app"

    def install_good(self, version: str = "3.40.0") -> None:
        r = self.apply(self.entry("noni-app", version, mod_zip(version, "good"), kind="mod"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("good", (self.app / "hooks" / "register.tsx").read_text())


class SafeUpdate(SyncCase):
    """Review: a bad App update must never delete the App that worked, and leave nothing to roll back to."""

    def assert_old_app_intact(self):
        self.assertIn("good", (self.app / "hooks" / "register.tsx").read_text())
        self.assertFalse((self.app / ".placeholder").exists())
        self.assertEqual(self.receipt()["noni-app"]["version"], "3.40.0")
        self.assertTrue((self.data / "packages" / "noni-app-3.40.0.zip").exists(), "old cached zip was dropped")
        self.assertFalse((self.data / "packages" / "noni-app-3.41.0.zip").exists(), "bad package was cached")

    def test_version_mismatch_keeps_working_app(self):
        self.install_good()
        r = self.apply(self.entry("noni-app", "3.41.0", mod_zip("9.9.9", "bad"), kind="mod"))
        self.assertNotEqual(r.returncode, 0)
        self.assert_old_app_intact()

    def test_broken_zip_keeps_working_app(self):
        self.install_good()
        r = self.apply(self.entry("noni-app", "3.41.0", b"this is not a zip", kind="mod"))
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("Traceback", r.stderr)
        self.assert_old_app_intact()

    def test_broken_zip_on_first_install_leaves_placeholder(self):
        r = self.apply(self.entry("noni-app", "3.40.0", b"this is not a zip", kind="mod"))
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("Traceback", r.stderr)
        self.assertTrue((self.app / ".placeholder").exists())
        self.assertTrue((self.app / "hooks" / "register.tsx").exists())

    def test_good_update_replaces_and_leaves_no_staging(self):
        self.install_good()
        r = self.apply(self.entry("noni-app", "3.41.0", mod_zip("3.41.0", "newer"), kind="mod"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("newer", (self.app / "hooks" / "register.tsx").read_text())
        self.assertEqual(self.receipt()["noni-app"]["version"], "3.41.0")
        self.assertEqual(sorted(p.name for p in (self.root / "mods").iterdir()), ["noni-app"])

    def test_one_failure_does_not_stop_or_unrecord_the_others(self):
        skill = self.entry("some-skill", "1.0.0", zip_bytes({"SKILL.md": "# s\n"}))
        r = self.apply(skill, self.entry("noni-app", "3.40.0", b"not a zip", kind="mod"))
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue((self.root / "skills" / "some-skill" / "SKILL.md").exists())
        self.assertIn("some-skill", self.receipt())
        self.assertNotIn("noni-app", self.receipt())

    def test_app_left_aside_by_a_killed_run_is_put_back(self):
        self.install_good()
        aside = self.root / "mods" / ".noni-app.previous"
        self.app.rename(aside)  # as if a run died between moving the App aside and moving the new one in
        r = self.apply(self.entry("noni-app", "3.41.0", b"not a zip", kind="mod"))
        self.assertNotEqual(r.returncode, 0)
        self.assert_old_app_intact()
        self.assertFalse(aside.exists())

    def test_restore_of_a_corrupt_cache_is_a_clean_refusal(self):
        # The SessionStart hook catches SystemExit only; any other exception used to escape it.
        sys.path.insert(0, str(SCRIPT.parent))
        try:
            import importlib
            ss = importlib.import_module("sync_skills")
            importlib.reload(ss)
            with self.assertRaises(SystemExit):
                ss.install_blob({"name": "noni-app", "version": "3.40.0", "kind": "mod"}, b"not a zip", self.root)
            self.assertTrue((self.app / ".placeholder").exists())
        finally:
            sys.path.remove(str(SCRIPT.parent))


class KnownModsOnly(SyncCase):
    """Review: a mod the plugin does not load must be refused, never marked installed."""

    def test_unknown_mod_is_refused(self):
        r = self.apply(self.entry("other-mod", "1.0.0", mod_zip("1.0.0"), kind="mod"))
        self.assertIn("REFUSED", r.stdout)
        self.assertIn("does not load a mod named", r.stdout)
        self.assertFalse((self.root / "mods" / "other-mod").exists())
        self.assertNotIn("other-mod", self.receipt())

    def test_registered_mod_is_installed(self):
        self.install_good()
        self.assertIn("noni-app", self.receipt())


class KindOf(SyncCase):
    """Review: only a missing `kind` means skill; an explicit empty or odd value is refused."""

    def test_empty_kind_is_refused_not_installed_as_skill(self):
        for bad in ("", None, 0, False, []):
            with self.subTest(kind=bad):
                r = self.apply(self.entry("odd", "1.0.0", zip_bytes({"SKILL.md": "# x\n"}), kind=bad))
                self.assertIn("REFUSED", r.stdout)
                self.assertFalse((self.root / "skills" / "odd").exists())

    def test_missing_kind_is_still_a_skill(self):
        r = self.apply(self.entry("plain", "1.0.0", zip_bytes({"SKILL.md": "# p\n"})))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.root / "skills" / "plain" / "SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()

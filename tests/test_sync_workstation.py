"""sync-skills installs into the user's workstation and never overwrites what the user changed.

Run from the repository root: python -m unittest discover -s tests -v
Packages are served from file:// URLs, so nothing touches the network.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "nonighter" / "skills" / "sync-skills" / "scripts" / "sync_skills.py"
HOOK = REPO / "nonighter" / "hooks" / "check_workstation.py"


def package(name: str, body: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:  # fixed timestamps: the same version is the same sha256
        z.writestr(zipfile.ZipInfo("SKILL.md", (2026, 1, 1, 0, 0, 0)), f"---\nname: {name}\n---\n{body}\n")
        z.writestr(zipfile.ZipInfo("scripts/run.py", (2026, 1, 1, 0, 0, 0)), f"print('{name} {body}')\n")
    return buf.getvalue()


class Sandbox:
    def __init__(self, workstation: bool = True):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.plugin = base / "plugin"
        self.data = base / "data"
        self.store = base / "store"
        self.ws = base / "work"
        for p in (self.plugin / "skills" / "sync-skills", self.store, self.ws):
            p.mkdir(parents=True)
        if workstation:
            (self.ws / ".nonighter").mkdir()
            (self.ws / ".nonighter" / "instance.json").write_text("{}", encoding="utf-8")

    def manifest(self, **skills: str) -> Path:
        entries = []
        for name, version in skills.items():
            name = name.replace("_", "-")
            blob = package(name, version)
            f = self.store / f"{name}-{version}.zip"
            f.write_bytes(blob)
            entries.append({"name": name, "version": version, "kind": "skill",
                            "sha256": hashlib.sha256(blob).hexdigest(), "url": f.as_uri()})
        m = self.store / "manifest.json"
        m.write_text(json.dumps({"tenant": "t1", "skills": entries}), encoding="utf-8")
        return m

    def run(self, *args: str) -> str:
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.ws))
        r = subprocess.run([sys.executable, str(SCRIPT), "--plugin-root", str(self.plugin),
                            "--data-dir", str(self.data), *args],
                           capture_output=True, text=True, env=env, cwd=self.ws)
        if r.returncode:
            raise AssertionError(r.stdout + r.stderr)
        return r.stdout

    def sync(self, *extra: str, **skills: str) -> str:
        return self.run("apply", "--manifest", str(self.manifest(**skills)), *extra)

    def receipt(self) -> dict:
        return json.loads((self.data / "sync-skills-receipt.json").read_text(encoding="utf-8"))

    def hook(self) -> str:
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.ws), CLAUDE_PLUGIN_DATA=str(self.data))
        # The hook finds its plugin from its own location, so run a copy placed in the sandbox plugin.
        hooks = self.plugin / "hooks"
        hooks.mkdir(exist_ok=True)
        (hooks / "check_workstation.py").write_text(HOOK.read_text(encoding="utf-8"), encoding="utf-8")
        scripts = self.plugin / "skills" / "sync-skills" / "scripts"
        scripts.mkdir(parents=True, exist_ok=True)
        (scripts / "sync_skills.py").write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
        r = subprocess.run([sys.executable, str(hooks / "check_workstation.py")], input="{}",
                           capture_output=True, text=True, env=env, cwd=self.ws)
        return r.stdout

    def ws_skill(self, name: str) -> Path:
        return self.ws / ".claude" / "skills" / name


class InstallsInTheWorkstation(unittest.TestCase):
    def test_without_a_workstation_skills_go_into_the_plugin(self):
        s = Sandbox(workstation=False)
        s.sync(modeling="1.0.0")
        self.assertTrue((s.plugin / "skills" / "modeling" / "SKILL.md").exists())
        self.assertFalse(s.ws_skill("modeling").exists())

    def test_with_a_workstation_skills_go_into_it_and_the_installer_stays_in_the_plugin(self):
        s = Sandbox()
        s.sync(modeling="1.0.0", workstation_init="0.17.1")
        self.assertTrue((s.ws_skill("modeling") / "SKILL.md").exists())
        self.assertTrue((s.plugin / "skills" / "workstation-init" / "SKILL.md").exists())
        self.assertFalse(s.ws_skill("workstation-init").exists())
        self.assertEqual(s.receipt()["workstation"], str(s.ws.resolve()))

    def test_a_skill_installed_before_workstations_moves_into_the_workstation(self):
        s = Sandbox(workstation=False)
        s.sync(modeling="1.0.0")
        r = s.receipt()  # an old receipt: no dest, no files
        for item in r["items"].values():
            item.pop("dest"), item.pop("files")
        (s.data / "sync-skills-receipt.json").write_text(json.dumps(r), encoding="utf-8")
        (s.ws / ".nonighter").mkdir()
        (s.ws / ".nonighter" / "instance.json").write_text("{}", encoding="utf-8")
        out = s.sync(modeling="1.0.0")
        self.assertIn("move", out)
        self.assertTrue((s.ws_skill("modeling") / "SKILL.md").exists())
        self.assertFalse((s.plugin / "skills" / "modeling").exists())

    def test_a_skill_the_user_wrote_with_the_same_name_is_never_overwritten(self):
        s = Sandbox()
        mine = s.ws_skill("modeling")
        mine.mkdir(parents=True)
        (mine / "SKILL.md").write_text("mine", encoding="utf-8")
        out = s.sync(modeling="1.0.0")
        self.assertIn("REFUSED", out)
        self.assertEqual((mine / "SKILL.md").read_text(encoding="utf-8"), "mine")


class KeepsWhatTheUserChanged(unittest.TestCase):
    def test_an_untouched_skill_is_updated(self):
        s = Sandbox()
        s.sync(modeling="1.0.0")
        out = s.sync(modeling="1.1.0")
        self.assertIn("update", out)
        self.assertIn("1.1.0", (s.ws_skill("modeling") / "SKILL.md").read_text(encoding="utf-8"))

    def test_a_changed_skill_is_not_overwritten_and_the_new_version_waits(self):
        s = Sandbox()
        s.sync(modeling="1.0.0")
        f = s.ws_skill("modeling") / "SKILL.md"
        f.write_text(f.read_text(encoding="utf-8") + "our firm's rule\n", encoding="utf-8")
        out = s.sync(modeling="1.1.0")
        self.assertIn("modified", out)
        self.assertIn("our firm's rule", f.read_text(encoding="utf-8"))
        item = s.receipt()["items"]["modeling"]
        self.assertEqual(item["version"], "1.0.0")
        self.assertEqual(item["available"]["version"], "1.1.0")
        # Both versions stay cached: the installed one is the merge base, the new one the update.
        cached = {z.name for z in (s.data / "packages").glob("*.zip")}
        self.assertEqual(cached, {"modeling-1.0.0.zip", "modeling-1.1.0.zip"})
        self.assertEqual(json.loads(s.run("status"))["updates_waiting"], {"modeling": "1.1.0"})

    def test_a_deleted_skill_is_not_brought_back_unless_asked(self):
        s = Sandbox()
        s.sync(modeling="1.0.0")
        import shutil
        shutil.rmtree(s.ws_skill("modeling"))
        self.assertIn("deleted", s.sync(modeling="1.0.0"))
        self.assertFalse(s.ws_skill("modeling").exists())
        self.assertIn("deleted", s.sync(modeling="1.1.0"))
        self.assertFalse(s.ws_skill("modeling").exists())
        s.sync("--reinstall", "modeling", modeling="1.1.0")
        self.assertTrue((s.ws_skill("modeling") / "SKILL.md").exists())

    def test_a_changed_skill_that_is_no_longer_licensed_is_kept(self):
        s = Sandbox()
        s.sync(modeling="1.0.0", decks="1.0.0")
        (s.ws_skill("decks") / "notes.md").write_text("mine", encoding="utf-8")
        out = s.sync(modeling="1.0.0")
        self.assertIn("kept", out)
        self.assertTrue((s.ws_skill("decks") / "notes.md").exists())


class StartupHook(unittest.TestCase):
    def test_the_hook_restores_plugin_skills_but_not_a_workstation_skill_the_user_deleted(self):
        s = Sandbox()
        s.sync(modeling="1.0.0", workstation_init="0.17.1")
        import shutil
        shutil.rmtree(s.plugin / "skills" / "workstation-init")  # a plugin update rebuilt the folder
        shutil.rmtree(s.ws_skill("modeling"))                     # the user deleted it
        out = s.hook()
        self.assertTrue((s.plugin / "skills" / "workstation-init" / "SKILL.md").exists())
        self.assertFalse(s.ws_skill("modeling").exists())
        self.assertIn("deleted from the user's workstation", out)


if __name__ == "__main__":
    unittest.main()

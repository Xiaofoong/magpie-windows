import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import release


def stable(tag, **overrides):
    return {"tag_name": tag, "draft": False, "prerelease": False, **overrides}


class ReleaseSelectionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.out = self.folder / "outputs"
        self.summary = self.folder / "summary"
        environment = patch.dict(os.environ, GITHUB_OUTPUT=str(self.out), GITHUB_STEP_SUMMARY=str(self.summary))
        environment.start()
        self.addCleanup(environment.stop)

    def job_outputs(self):
        return dict(line.split("=", 1) for line in self.out.read_text().splitlines())

    def test_current_core_is_only_rebuilt_for_validation(self):
        core = "v0.1.4288"
        current = f"{core}-workbuddy.{release.REVISION}"
        with patch.object(release, "gh_api", side_effect=[stable(core), [stable(current)]] * 2):
            release.plan("example/windows")
            self.assertEqual(self.job_outputs()["build"], "false")
            release.plan("example/windows", validate_current=True)
            self.assertEqual(self.job_outputs()["build"], "true")

    def test_alternatives_are_bounded_stable_and_newer_than_published(self):
        published = (0, 1, 4250, release.REVISION)
        versions = [stable(f"v0.1.{n}") for n in (4255, 4261, 4250, 4260, 4257, 4249, 4256)]
        versions.extend([stable("v0.1.4259", draft=True), stable("v0.1.4258", prerelease=True)])
        with patch.object(release, "gh_api", return_value=versions):
            self.assertEqual(release.fallback_cores("v0.1.4260", published),
                             ["v0.1.4257", "v0.1.4256", "v0.1.4255"])
            self.assertEqual(len(release.fallback_cores("v0.1.4262", published)), release.MAX_FALLBACKS)

    def set_up_source(self):
        origin = self.folder / "origin"
        origin.mkdir()
        git = ["git", "-C", str(origin)]

        def run(*args):
            return subprocess.check_output([*git, *args])

        run("init", "--quiet")
        run("config", "user.name", "CI fixture")
        run("config", "user.email", "ci@example.invalid")
        app = origin / "app.js"
        app.write_text("baseline\n")
        run("add", "app.js")
        run("commit", "--quiet", "-m", "baseline")
        run("tag", release.BASE)
        app.write_text("custom\n")
        (self.folder / "workbuddy.patch").write_bytes(run("diff", "--full-index"))
        run("restore", "app.js")
        (origin / "official.txt").write_text("official feature\n")
        run("add", "official.txt")
        run("commit", "--quiet", "-m", "compatible")
        run("tag", "v0.1.4250")
        app.write_text("upstream conflict\n")
        run("commit", "--quiet", "-am", "conflicting")
        run("tag", "v0.1.4251")
        overrides = patch.multiple(release, SOURCE=origin.as_uri(), ROOT=self.folder)
        overrides.start()
        self.addCleanup(overrides.stop)
        return self.folder / "source"

    def test_real_patch_conflict_falls_back_to_compatible_core(self):
        source = self.set_up_source()
        with patch.object(release, "gh_api", return_value=[stable("v0.1.4250")]):
            release.prepare(source, "v0.1.4251", f"v0.1.4249-workbuddy.{release.REVISION}")
        self.assertEqual(self.job_outputs()["core"], "v0.1.4250")
        self.assertEqual(self.job_outputs()["publish"], "true")
        self.assertEqual((source / "app.js").read_text(), "custom\n")
        self.assertIn("`app.js`", self.summary.read_text())

    def test_conflict_cannot_republish_the_already_published_core(self):
        source = self.set_up_source()
        current = f"v0.1.4250-workbuddy.{release.REVISION}"
        with patch.object(release, "gh_api", return_value=[stable("v0.1.4250")]):
            release.prepare(source, "v0.1.4251", current)
        self.assertEqual(self.job_outputs(), {"ready": "false", "publish": "false"})
        self.assertIn(current, self.summary.read_text())

    def test_validation_build_does_not_publish(self):
        source = self.set_up_source()
        release.prepare(source, "v0.1.4250", f"v0.1.4250-workbuddy.{release.REVISION}")
        self.assertEqual(self.job_outputs()["ready"], "true")
        self.assertEqual(self.job_outputs()["publish"], "false")

    def test_malformed_patch_surfaces_a_failure(self):
        source = self.set_up_source()
        (self.folder / "workbuddy.patch").write_text("not a patch\n")
        with self.assertRaises(subprocess.CalledProcessError):
            release.prepare(source, "v0.1.4250", "")
        self.assertFalse(self.out.exists())


class InstallerPackageTest(unittest.TestCase):
    def test_final_manifest_requires_both_installers(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            with self.assertRaises(FileNotFoundError):
                release.seal(directory)
            self.assertFalse((directory / "SHA256SUMS.txt").exists())

    def test_installers_and_programs_are_all_hashed(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            header = bytearray(64)
            header[:2] = b"MZ"
            struct.pack_into("<I", header, 60, 64)
            installer = header + b"PE\0\0\x4c\x01"
            for name in release.assets():
                if name != "SHA256SUMS.txt":
                    data = installer if name.endswith("-Setup.exe") else b"package fixture"
                    (directory / name).write_bytes(data)
            release.seal(directory)
            lines = (directory / "SHA256SUMS.txt").read_text().splitlines()
            self.assertEqual(len(lines), 6)
            for line in lines:
                digest, name = line.split("  ")
                self.assertEqual(digest, release.file_hash(directory / name))
            (directory / "Magpie-Windows-ARM64-Setup.exe").write_bytes(b"invalid")
            with self.assertRaises(ValueError):
                release.seal(directory)


if __name__ == "__main__":
    unittest.main()

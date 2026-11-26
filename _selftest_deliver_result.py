#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""云端文件交付自检；默认离线，--online 额外下载五份实际资源。

所有测试产物只写入本次独立临时目录，结束后自动清理。
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from http.client import IncompleteRead
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "scripts" / "deliver_result.py"
spec = importlib.util.spec_from_file_location("deliver_result", SCRIPT)
delivery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delivery)
ONLINE = "--online" in sys.argv
if ONLINE:
    sys.argv.remove("--online")


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="gear-delivery-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.skill = self.base / "skill"
        self.outputs = self.base / "outputs"
        self.bodies = {}
        manifests = {}
        for kind, relative in delivery.RESULTS.items():
            filename = delivery.resource_for(kind)["filename"]
            body = (kind + "\n测试原始内容\n").encode("utf-8")
            url = "https://assets.example.test/" + kind
            self.bodies[url] = body
            data = manifests.setdefault(relative, {"schema_version": 1, "files": {}})
            data["files"][kind] = {
                "url": url, "filename": filename, "size_bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
            }
        for relative, data in manifests.items():
            manifest = self.skill / relative
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        root_patch = patch.object(delivery, "SKILL_ROOT", self.skill)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        remote_patch = patch.object(delivery, "open_remote", side_effect=lambda url: io.BytesIO(self.bodies[url]))
        self.remote = remote_patch.start()
        self.addCleanup(remote_patch.stop)

    def change_resource(self, **changes):
        manifest = self.skill / delivery.RESULTS["control-plan"]
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["files"]["control-plan"].update(changes)
        manifest.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def test_all_five_kinds_are_byte_identical(self):
        for kind in delivery.RESULTS:
            with self.subTest(kind=kind):
                resource = delivery.resource_for(kind)
                result = delivery.deliver_result(kind, self.outputs)
                target = Path(result["output"])
                self.assertEqual(target.name, resource["filename"])
                self.assertEqual(target.read_bytes(), self.bodies[resource["url"]])
                self.assertEqual(result["sha256"], resource["sha256"])
                self.assertTrue(result["verified"])
                self.assertEqual(result["status"], "success")
                self.assertEqual(list(target.parent.iterdir()), [target])
        self.assertEqual(list(self.skill.rglob("*.pdf")), [])
        self.assertEqual(list(self.skill.rglob("*.xlsx")), [])

    def test_repeated_delivery_never_overwrites(self):
        first = delivery.deliver_result("control-plan", self.outputs)
        path = Path(first["output"])
        original = path.read_bytes()
        second = delivery.deliver_result("control-plan", self.outputs)
        self.assertNotEqual(first["output"], second["output"])
        self.assertEqual(path.read_bytes(), original)

    def test_existing_files_in_output_root_are_preserved(self):
        self.outputs.mkdir()
        existing = self.outputs / "控制计划.xlsx"
        existing.write_bytes(b"user document")
        delivery.deliver_result("control-plan", self.outputs)
        self.assertEqual(existing.read_bytes(), b"user document")

    def test_verify_is_read_only_and_offline(self):
        result = delivery.deliver_result("control-plan", self.outputs)
        path = Path(result["output"])
        before = path.stat().st_mtime_ns
        self.remote.reset_mock()
        checked = delivery.verify_result("control-plan", path)
        self.assertEqual(result, checked)
        self.assertEqual(path.stat().st_mtime_ns, before)
        self.remote.assert_not_called()

    def test_modified_file_is_rejected_without_deletion(self):
        result = delivery.deliver_result("control-plan", self.outputs)
        path = Path(result["output"])
        modified = b"X" * path.stat().st_size
        path.write_bytes(modified)
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            delivery.verify_result("control-plan", path)
        self.assertEqual(path.read_bytes(), modified)

    def test_missing_manifest_does_not_create_output(self):
        (self.skill / delivery.RESULTS["control-plan"]).unlink()
        with self.assertRaises(ValueError):
            delivery.deliver_result("control-plan", self.outputs)
        self.assertFalse(self.outputs.exists())
        self.remote.assert_not_called()

    def test_invalid_resource_cannot_download(self):
        for change in [
            {"filename": "../outside.pdf"}, {"filename": "..\\outside.pdf"},
            {"filename": "C:outside.pdf"}, {"url": "file:///secret.pdf"},
            {"url": "http://assets.example.test/file.pdf"},
            {"url": "https://user:secret@assets.example.test/file.pdf"},
            {"size_bytes": 0}, {"sha256": "invalid"},
        ]:
            with self.subTest(change=change):
                manifest = self.skill / delivery.RESULTS["control-plan"]
                original = manifest.read_bytes()
                try:
                    self.change_resource(**change)
                    with self.assertRaises(ValueError):
                        delivery.deliver_result("control-plan", self.outputs)
                    self.assertFalse(self.outputs.exists())
                    self.remote.assert_not_called()
                finally:
                    manifest.write_bytes(original)

    def test_invalid_json_is_rejected(self):
        (self.skill / delivery.RESULTS["control-plan"]).write_text("{broken", encoding="utf-8")
        with self.assertRaises(ValueError):
            delivery.deliver_result("control-plan", self.outputs)
        self.assertFalse(self.outputs.exists())

    def test_output_inside_skill_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "技能目录"):
            delivery.deliver_result("control-plan", self.skill / "outputs")
        self.assertFalse((self.skill / "outputs").exists())

    def test_file_inside_skill_cannot_be_used_as_deliverable(self):
        resource = delivery.resource_for("control-plan")
        path = self.skill / "source.xlsx"
        path.write_bytes(self.bodies[resource["url"]])
        with self.assertRaisesRegex(ValueError, "技能目录"):
            delivery.verify_result("control-plan", path)

    def test_missing_output_is_rejected(self):
        with self.assertRaises(ValueError):
            delivery.verify_result("control-plan", self.base / "missing.xlsx")

    def test_existing_file_cannot_be_output_root(self):
        self.outputs.write_bytes(b"existing file")
        with self.assertRaises(OSError):
            delivery.deliver_result("control-plan", self.outputs)
        self.assertEqual(self.outputs.read_bytes(), b"existing file")

    def test_bad_downloads_remove_only_new_files(self):
        resource = delivery.resource_for("control-plan")
        original = self.bodies[resource["url"]]
        self.outputs.mkdir()
        keep = self.outputs / "keep.txt"
        keep.write_bytes(b"keep")
        for body in [b"", original[:-1], original + b"extra", b"X" * len(original)]:
            with self.subTest(size=len(body)):
                self.bodies[resource["url"]] = body
                with self.assertRaises(ValueError):
                    delivery.deliver_result("control-plan", self.outputs)
                self.assertEqual(list(self.outputs.iterdir()), [keep])
                self.assertEqual(keep.read_bytes(), b"keep")

    def test_network_errors_remove_task_directory(self):
        for error in [URLError("unavailable"), TimeoutError("timeout"),
                      HTTPError("https://example.test/missing", 404, "missing", {}, None)]:
            with self.subTest(error=type(error).__name__):
                self.remote.side_effect = error
                with self.assertRaises(OSError):
                    delivery.deliver_result("control-plan", self.outputs)
                self.assertEqual(list(self.outputs.iterdir()), [])

    def test_interrupted_stream_removes_partial_file(self):
        for error in [IncompleteRead(b"partial", 10), KeyboardInterrupt()]:
            with self.subTest(error=type(error).__name__):
                stream = io.BytesIO(b"partial")
                with patch.object(stream, "read", side_effect=[b"partial", error]):
                    self.remote.side_effect = None
                    self.remote.return_value = stream
                    with self.assertRaises(type(error)):
                        delivery.deliver_result("control-plan", self.outputs)
                self.assertEqual(list(self.outputs.iterdir()), [])

    def test_failed_verification_removes_only_new_file(self):
        self.outputs.mkdir()
        keep = self.outputs / "keep.txt"
        keep.write_bytes(b"keep")
        with patch.object(delivery, "verify_result", side_effect=ValueError("test mismatch")):
            with self.assertRaisesRegex(ValueError, "test mismatch"):
                delivery.deliver_result("control-plan", self.outputs)
        self.assertEqual(list(self.outputs.iterdir()), [keep])

    def test_streams_multiple_chunks(self):
        with patch.object(delivery, "CHUNK_SIZE", 7):
            result = delivery.deliver_result("control-plan", self.outputs)
        resource = delivery.resource_for("control-plan")
        self.assertEqual(Path(result["output"]).read_bytes(), self.bodies[resource["url"]])

    def test_https_redirect_cannot_downgrade(self):
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            delivery.HTTPSRedirectHandler().redirect_request(
                Request("https://example.test/a"), None, 302, "Found", {}, "http://example.test/b")

    def test_cli_delivery_success_and_network_failure(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = delivery.main(["--kind", "control-plan", "--output-root", str(self.outputs)])
        self.assertEqual(code, 0, stderr.getvalue())
        self.assertTrue(json.loads(stdout.getvalue())["verified"])
        stdout, stderr = io.StringIO(), io.StringIO()
        self.remote.side_effect = URLError("unavailable")
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = delivery.main(["--kind", "control-plan", "--output-root", str(self.outputs)])
        self.assertEqual(code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertFalse(json.loads(stderr.getvalue())["verified"])


class InstalledFilesTests(unittest.TestCase):
    def test_all_manifests_are_valid_and_contain_exact_kinds(self):
        for relative in set(delivery.RESULTS.values()):
            data = json.loads((ROOT / relative).read_text(encoding="utf-8"))
            self.assertEqual(set(data["files"]), {kind for kind, path in delivery.RESULTS.items() if path == relative})
        for kind in delivery.RESULTS:
            self.assertTrue(delivery.resource_for(kind)["url"].startswith("https://"))

    def test_invalid_kind_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="gear-delivery-invalid-") as temp:
            result = subprocess.run(
                [sys.executable, "-I", "-B", str(SCRIPT), "--kind", "assembly",
                 "--output-root", str(Path(temp) / "outputs")],
                capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertFalse((Path(temp) / "outputs").exists())

    def test_cli_reports_verify_failure(self):
        with tempfile.TemporaryDirectory(prefix="gear-delivery-error-") as temp:
            result = subprocess.run(
                [sys.executable, "-I", "-B", str(SCRIPT), "--kind", "control-plan",
                 "--verify", str(Path(temp) / "missing.xlsx")],
                capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            data = json.loads(result.stderr)
            self.assertEqual(data["status"], "error")
            self.assertFalse(data["verified"])

    @unittest.skipUnless(ONLINE, "使用 --online 执行实际云端下载测试")
    def test_five_cloud_resources_via_cli(self):
        with tempfile.TemporaryDirectory(prefix="gear-delivery-online-") as temp:
            for kind in delivery.RESULTS:
                with self.subTest(kind=kind):
                    resource = delivery.resource_for(kind)
                    result = subprocess.run(
                        [sys.executable, "-I", "-B", str(SCRIPT), "--kind", kind,
                         "--output-root", str(Path(temp) / "交付目录")],
                        capture_output=True, text=True, encoding="utf-8", check=False, timeout=60,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    data = json.loads(result.stdout)
                    output = Path(data["output"])
                    self.assertEqual(output.name, resource["filename"])
                    self.assertEqual(delivery.sha256(output), resource["sha256"])
                    self.assertEqual(output.stat().st_size, resource["size_bytes"])
                    checked = subprocess.run(
                        [sys.executable, "-I", "-B", str(SCRIPT), "--kind", kind,
                         "--verify", str(output)],
                        capture_output=True, text=True, encoding="utf-8", check=False,
                    )
                    self.assertEqual(checked.returncode, 0, checked.stderr)
                    self.assertTrue(json.loads(checked.stdout)["verified"])
                    self.assertEqual(list(output.parent.iterdir()), [output])


if __name__ == "__main__":
    unittest.main(verbosity=2)

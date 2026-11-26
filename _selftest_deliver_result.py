#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""固定交付自检：只在独立临时目录生成测试副本，不改动内置结果文件。"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "scripts" / "deliver_result.py"
spec = importlib.util.spec_from_file_location("deliver_result", SCRIPT)
delivery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delivery)


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="gear-delivery-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.skill = self.base / "skill"
        self.outputs = self.base / "outputs"
        for kind, (relative, _) in delivery.RESULTS.items():
            source = self.skill / relative
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes((kind + "\n测试原始内容\n").encode("utf-8"))
        self.root_patch = patch.object(delivery, "SKILL_ROOT", self.skill)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def test_both_kinds_are_byte_identical(self):
        for kind, (relative, filename) in delivery.RESULTS.items():
            with self.subTest(kind=kind):
                source = self.skill / relative
                original = source.read_bytes()
                result = delivery.deliver_result(kind, self.outputs)
                target = Path(result["output"])
                self.assertEqual(target.name, filename)
                self.assertEqual(target.read_bytes(), original)
                self.assertEqual(source.read_bytes(), original)
                self.assertEqual(result["sha256"], delivery.sha256(source))
                self.assertTrue(result["verified"])
                self.assertEqual(result["status"], "success")
                self.assertEqual(list(target.parent.iterdir()), [target])

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

    def test_verify_is_read_only(self):
        result = delivery.deliver_result("control-plan", self.outputs)
        path = Path(result["output"])
        before = path.stat().st_mtime_ns
        checked = delivery.verify_result("control-plan", path)
        self.assertEqual(result, checked)
        self.assertEqual(path.stat().st_mtime_ns, before)

    def test_modified_file_is_rejected_without_deletion(self):
        result = delivery.deliver_result("control-plan", self.outputs)
        path = Path(result["output"])
        path.write_bytes(b"changed workbook")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            delivery.verify_result("control-plan", path)
        self.assertEqual(path.read_bytes(), b"changed workbook")

    def test_missing_source_does_not_create_output(self):
        source = delivery.source_for("control-plan")
        source.unlink()
        with self.assertRaises(ValueError):
            delivery.deliver_result("control-plan", self.outputs)
        self.assertFalse(self.outputs.exists())

    def test_empty_source_is_rejected(self):
        source = delivery.source_for("control-plan")
        source.write_bytes(b"")
        with self.assertRaisesRegex(ValueError, "为空"):
            delivery.deliver_result("control-plan", self.outputs)
        self.assertFalse(self.outputs.exists())

    def test_output_inside_skill_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "技能目录"):
            delivery.deliver_result("control-plan", self.skill / "outputs")
        self.assertFalse((self.skill / "outputs").exists())

    def test_source_cannot_be_used_as_deliverable(self):
        with self.assertRaisesRegex(ValueError, "技能目录"):
            delivery.verify_result("control-plan", delivery.source_for("control-plan"))

    def test_missing_output_is_rejected(self):
        with self.assertRaises(ValueError):
            delivery.verify_result("control-plan", self.base / "missing.xlsx")

    def test_existing_file_cannot_be_output_root(self):
        self.outputs.write_bytes(b"existing file")
        with self.assertRaises(OSError):
            delivery.deliver_result("control-plan", self.outputs)
        self.assertEqual(self.outputs.read_bytes(), b"existing file")

    def test_failed_verification_removes_only_new_copy(self):
        self.outputs.mkdir()
        keep = self.outputs / "keep.txt"
        keep.write_bytes(b"keep")
        with patch.object(delivery, "verify_result", side_effect=ValueError("test mismatch")):
            with self.assertRaisesRegex(ValueError, "test mismatch"):
                delivery.deliver_result("control-plan", self.outputs)
        self.assertEqual(list(self.outputs.iterdir()), [keep])
        self.assertEqual(keep.read_bytes(), b"keep")

    def test_changing_source_does_not_report_success(self):
        original_sha = delivery.sha256
        source = delivery.source_for("control-plan")
        calls = []

        def changing_sha(path):
            if path == source:
                calls.append(path)
                if len(calls) >= 2:
                    return "0" * 64
            return original_sha(path)

        with patch.object(delivery, "sha256", side_effect=changing_sha):
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                delivery.deliver_result("control-plan", self.outputs)
        self.assertEqual(list(self.outputs.iterdir()), [])


class InstalledFilesTests(unittest.TestCase):
    def test_installed_pdf_and_xlsx_via_cli(self):
        with tempfile.TemporaryDirectory(prefix="gear-delivery-cli-") as temp:
            for kind, (relative, filename) in delivery.RESULTS.items():
                with self.subTest(kind=kind):
                    source = ROOT / relative
                    source_hash = delivery.sha256(source)
                    result = subprocess.run(
                        [sys.executable, "-I", "-B", str(SCRIPT), "--kind", kind,
                         "--output-root", str(Path(temp) / "交付目录")],
                        capture_output=True, text=True, encoding="utf-8", check=False,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    data = json.loads(result.stdout)
                    output = Path(data["output"])
                    self.assertEqual(output.name, filename)
                    self.assertEqual(data["sha256"], source_hash)
                    self.assertEqual(delivery.sha256(output), source_hash)
                    checked = subprocess.run(
                        [sys.executable, "-I", "-B", str(SCRIPT), "--kind", kind,
                         "--verify", str(output)],
                        capture_output=True, text=True, encoding="utf-8", check=False,
                    )
                    self.assertEqual(checked.returncode, 0, checked.stderr)
                    self.assertTrue(json.loads(checked.stdout)["verified"])
                    self.assertEqual(delivery.sha256(source), source_hash)

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


if __name__ == "__main__":
    unittest.main(verbosity=2)

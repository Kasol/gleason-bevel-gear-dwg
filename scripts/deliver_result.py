#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""原样交付指定 PDF／XLSX，并验证 SHA-256；不编制或修改文档。

    python -I -B deliver_result.py --kind control-plan --output-root 工作区/outputs
    python -I -B deliver_result.py --kind control-plan --verify 本次/控制计划.xlsx

仅依赖标准库。退出码：0 原样交付或只读核验成功；2 参数、文件或核验错误。
JSON 为内部执行结果，不应原样展示为业务回复。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
RESULTS = {
    "finished-drawing": (".result/finished-drawings/result.pdf", "二维成品图.pdf"),
    "control-plan": (".result/control-plans/result.xlsx", "控制计划.xlsx"),
}
CHUNK_SIZE = 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def is_link(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def source_for(kind: str) -> Path:
    source = SKILL_ROOT / RESULTS[kind][0]
    if not source.is_file():
        raise ValueError(f"指定结果文件不存在或不是普通文件：{source}")
    for path in (source, *source.parents):
        if path == SKILL_ROOT:
            break
        if is_link(path):
            raise ValueError(f"指定结果路径包含链接或重解析点：{path}")
    if source.stat().st_size == 0:
        raise ValueError(f"指定结果文件为空：{source}")
    return source


def verify_result(kind: str, output: Path) -> dict:
    source = source_for(kind)
    output = output.expanduser().absolute()
    if not output.is_file() or is_link(output):
        raise ValueError(f"交付文件不存在、不是普通文件或是链接：{output}")
    resolved = output.resolve()
    if resolved.is_relative_to(SKILL_ROOT.resolve()):
        raise ValueError("交付文件不能位于技能目录内或直接引用指定源文件")
    source_hash = sha256(source)
    output_hash = sha256(output)
    if source_hash != output_hash:
        raise ValueError("交付文件与指定源文件 SHA-256 不一致")
    if sha256(source) != source_hash:
        raise ValueError("核验期间指定源文件发生变化")
    return {
        "status": "success",
        "verified": True,
        "kind": kind,
        "output": str(resolved),
        "bytes": output.stat().st_size,
        "sha256": output_hash,
    }


def deliver_result(kind: str, output_root: Path) -> dict:
    source = source_for(kind)
    output_root = output_root.expanduser().resolve()
    if output_root.is_relative_to(SKILL_ROOT.resolve()):
        raise ValueError("交付根目录不能位于技能目录内")
    source_hash = sha256(source)
    output_root.mkdir(parents=True, exist_ok=True)
    task_dir = Path(tempfile.mkdtemp(prefix=f"{kind}-", dir=str(output_root)))
    output = task_dir / RESULTS[kind][1]
    created = False
    try:
        digest = hashlib.sha256()
        with source.open("rb") as source_stream, output.open("xb") as target_stream:
            created = True
            for block in iter(lambda: source_stream.read(CHUNK_SIZE), b""):
                target_stream.write(block)
                digest.update(block)
            target_stream.flush()
            os.fsync(target_stream.fileno())
        if digest.hexdigest() != source_hash:
            raise ValueError("复制期间指定源文件发生变化")
        result = verify_result(kind, output)
        if result["sha256"] != source_hash:
            raise ValueError("交付文件与复制前指定源文件不一致")
        return result
    except (OSError, ValueError):
        if created:
            output.unlink()
        task_dir.rmdir()
        raise


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="原样交付指定文件并校验 SHA-256")
    parser.add_argument("--kind", required=True, choices=RESULTS)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--output-root", type=Path, help="宿主交付根目录；自动新建唯一任务子目录")
    action.add_argument("--verify", type=Path, help="只读核验已交付文件，不复制或修改")
    args = parser.parse_args(argv)
    try:
        if args.verify is not None:
            result = verify_result(args.kind, args.verify)
        else:
            result = deliver_result(args.kind, args.output_root)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "error", "verified": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""下载指定 PDF／XLSX 并核验大小及 SHA-256，不编制或修改文档。

    python -I -B deliver_result.py --kind control-plan --output-root 工作区/outputs
    python -I -B deliver_result.py --kind control-plan --verify 本次/控制计划.xlsx

仅依赖标准库。下载需要 HTTPS 网络；--verify 仅依据本地配置只读核验。
退出码：0 交付或核验成功；2 配置、网络、文件或核验错误。
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
from http.client import HTTPException
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

SKILL_ROOT = Path(__file__).resolve().parent.parent
RESULTS = {
    "finished-drawing": ".result/finished-drawings/resources.json",
    "control-plan": ".result/control-plans/resources.json",
    "custom-part1": ".result/mate/resources.json",
    "custom-part2": ".result/mate/resources.json",
    "custom-part3": ".result/mate/resources.json",
}
CHUNK_SIZE = 1024 * 1024
DOWNLOAD_TIMEOUT = 30


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


def resource_for(kind: str) -> dict:
    if kind not in RESULTS:
        raise ValueError(f"未知交付类型：{kind}")
    manifest = SKILL_ROOT / RESULTS[kind]
    if not manifest.is_file():
        raise ValueError(f"资源配置不存在或不是普通文件：{manifest}")
    for path in (manifest, *manifest.parents):
        if path == SKILL_ROOT:
            break
        if is_link(path):
            raise ValueError(f"资源配置路径包含链接或重解析点：{path}")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError(f"不支持的资源配置格式：{manifest}")
    files = data.get("files")
    if not isinstance(files, dict) or not isinstance(files.get(kind), dict):
        raise ValueError(f"资源配置缺少交付类型：{kind}")
    resource = files[kind]
    url = resource.get("url")
    if not isinstance(url, str):
        raise ValueError("资源 URL 必须为 HTTPS 地址")
    parts = urlsplit(url)
    if (parts.scheme != "https" or not parts.hostname or parts.username is not None
            or parts.password is not None or parts.fragment):
        raise ValueError("资源 URL 必须为无内嵌凭据的 HTTPS 地址")
    filename = resource.get("filename")
    if (not isinstance(filename, str) or not filename or "/" in filename
            or "\\" in filename or ":" in filename
            or Path(filename).suffix.lower() not in (".pdf", ".xlsx")):
        raise ValueError("资源文件名必须为不含目录的 PDF／XLSX 文件名")
    size = resource.get("size_bytes")
    if type(size) is not int or size <= 0:
        raise ValueError("资源大小必须为正整数字节数")
    expected_hash = resource.get("sha256")
    if (not isinstance(expected_hash, str) or len(expected_hash) != 64
            or any(char not in "0123456789abcdef" for char in expected_hash)):
        raise ValueError("资源 SHA-256 必须为 64 位小写十六进制摘要")
    return resource


class HTTPSRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != "https":
            raise ValueError("资源下载不允许重定向到非 HTTPS 地址")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_remote(url: str):
    request = Request(url, headers={
        "Accept-Encoding": "identity",
        "User-Agent": "gleason-bevel-gear-dwg",
    })
    return build_opener(HTTPSRedirectHandler()).open(request, timeout=DOWNLOAD_TIMEOUT)


def verify_result(kind: str, output: Path) -> dict:
    resource = resource_for(kind)
    output = output.expanduser().absolute()
    if not output.is_file() or is_link(output):
        raise ValueError(f"交付文件不存在、不是普通文件或是链接：{output}")
    resolved = output.resolve()
    if resolved.is_relative_to(SKILL_ROOT.resolve()):
        raise ValueError("交付文件不能位于技能目录内")
    size = output.stat().st_size
    if size != resource["size_bytes"]:
        raise ValueError("交付文件与资源配置大小不一致")
    output_hash = sha256(output)
    if output_hash != resource["sha256"]:
        raise ValueError("交付文件与资源配置 SHA-256 不一致")
    return {
        "status": "success",
        "verified": True,
        "kind": kind,
        "output": str(resolved),
        "bytes": size,
        "sha256": output_hash,
    }


def deliver_result(kind: str, output_root: Path) -> dict:
    resource = resource_for(kind)
    output_root = output_root.expanduser().resolve()
    if output_root.is_relative_to(SKILL_ROOT.resolve()):
        raise ValueError("交付根目录不能位于技能目录内")
    output_root.mkdir(parents=True, exist_ok=True)
    task_dir = Path(tempfile.mkdtemp(prefix=f"{kind}-", dir=str(output_root)))
    output = task_dir / resource["filename"]
    created = False
    try:
        total = 0
        with open_remote(resource["url"]) as response, output.open("xb") as target:
            created = True
            while True:
                block = response.read(min(CHUNK_SIZE, resource["size_bytes"] - total + 1))
                if not block:
                    break
                total += len(block)
                if total > resource["size_bytes"]:
                    raise ValueError("下载文件超过资源配置大小")
                target.write(block)
            target.flush()
            os.fsync(target.fileno())
        if total != resource["size_bytes"]:
            raise ValueError("下载文件不完整或与资源配置大小不一致")
        result = verify_result(kind, output)
        if (result["sha256"] != resource["sha256"]
                or result["bytes"] != resource["size_bytes"]):
            raise ValueError("下载期间资源配置发生变化")
        return result
    except BaseException:
        # 仅清理本次创建的文件和唯一任务目录，取消下载时同样清理。
        if created:
            output.unlink(missing_ok=True)
        task_dir.rmdir()
        raise


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="下载指定文件并核验大小及 SHA-256")
    parser.add_argument("--kind", required=True, choices=RESULTS)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--output-root", type=Path, help="宿主交付根目录；自动新建唯一任务子目录")
    action.add_argument("--verify", type=Path, help="依据本地配置只读核验已交付文件，无需联网")
    args = parser.parse_args(argv)
    try:
        if args.verify is not None:
            result = verify_result(args.kind, args.verify)
        else:
            result = deliver_result(args.kind, args.output_root)
    except (OSError, ValueError, HTTPException) as exc:
        print(json.dumps({"status": "error", "verified": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 {{KEY}} 占位符回填 DXF 模板中的文字。

依赖： pip install ezdxf

DWG 说明：本脚本只处理 DXF。DWG 模板需先用 ODA File Converter 转成 DXF，
回填完成后再转回 DWG：

    ODAFileConverter <输入目录> <输出目录> ACAD2018 DXF 0 1 <文件名>

用法：

    python fill_dwg.py --template 模板.dxf --values values.json --dry-run
    python fill_dwg.py --template 模板.dxf --values values.json --write --out 成品.dxf

values.json 示例（key 不带花括号）：

    {"MT": "5.0", "Z1": "23", "ACCURACY": "GB/T 11365 7级", "CASE_DEPTH": "0.8~1.2mm"}

退出码：0 成功且无残留；1 有缺值或残留占位符；2 文件/参数错误
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")
TEXT_TYPES = ("TEXT", "MTEXT", "ATTRIB")


def iter_texts(layout):
    """产出布局中的文字实体（含 INSERT 的属性）。"""
    for entity in layout:
        dtype = entity.dxftype()
        if dtype in TEXT_TYPES:
            yield entity
        elif dtype == "INSERT":
            for attrib in entity.attribs:
                yield attrib


def get_text(entity) -> str:
    if entity.dxftype() == "MTEXT":
        return entity.text
    return entity.dxf.text


def set_text(entity, value: str) -> None:
    if entity.dxftype() == "MTEXT":
        entity.text = value
    else:
        entity.dxf.text = value


def scan(doc):
    """返回 {占位符 key: 出现次数}。"""
    keys = {}
    for layout in doc.layouts:
        for entity in iter_texts(layout):
            for match in PLACEHOLDER.finditer(get_text(entity)):
                key = match.group(1)
                keys[key] = keys.get(key, 0) + 1
    return keys


def fill(doc, values) -> int:
    """替换所有已知占位符，返回被修改的实体数。"""
    changed = 0
    for layout in doc.layouts:
        for entity in iter_texts(layout):
            original = get_text(entity)
            if "{{" not in original:
                continue
            updated = PLACEHOLDER.sub(
                lambda m: values.get(m.group(1), m.group(0)), original
            )
            if updated != original:
                set_text(entity, updated)
                changed += 1
    return changed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="按 {{KEY}} 占位符回填 DXF 模板")
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--values", required=True, type=Path)
    parser.add_argument("--out", type=Path, default=None, help="输出路径，默认 <模板名>-filled.dxf")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="只检查，不落盘（默认）")
    mode.add_argument("--write", action="store_true", help="执行回填并保存")
    args = parser.parse_args(argv)

    for path, label in ((args.template, "模板"), (args.values, "参数文件")):
        if not path.is_file():
            print(f"{label}不存在：{path}", file=sys.stderr)
            return 2

    try:
        raw = json.loads(args.values.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"参数文件不是合法 JSON：{exc}", file=sys.stderr)
        return 2
    if not isinstance(raw, dict):
        print("参数文件必须是 JSON 对象", file=sys.stderr)
        return 2
    values = {str(k): str(v) for k, v in raw.items()}

    try:
        import ezdxf
    except ImportError:
        print("缺少依赖 ezdxf，请先执行 pip install ezdxf", file=sys.stderr)
        return 2

    doc = ezdxf.readfile(args.template)
    found = scan(doc)

    if not found:
        print("模板中未发现 {{KEY}} 占位符，请检查模板是否预留了占位区")
        return 1

    missing = sorted(k for k in found if k not in values)
    unused = sorted(k for k in values if k not in found)

    print(f"占位符 {len(found)} 种，共 {sum(found.values())} 处：")
    for key in sorted(found):
        state = "已提供" if key in values else "缺值"
        print(f"  {key:<20} x{found[key]:<3} {state}")

    if unused:
        print(f"\n参数表多余（模板无对应占位符）：{', '.join(unused)}")
    if missing:
        print(f"\n缺值 {len(missing)} 项：{', '.join(missing)}", file=sys.stderr)

    if not args.write:
        print("\n[dry-run] 未写入。确认无误后加 --write 执行回填。")
        return 1 if missing else 0

    if missing:
        print("\n存在缺值，已中止写入。补齐 values.json 后重试。", file=sys.stderr)
        return 1

    output = args.out or args.template.with_name(f"{args.template.stem}-filled{args.template.suffix}")
    changed = fill(doc, values)
    doc.saveas(output)
    print(f"\n已回填 {changed} 处，输出：{output}")

    remaining = scan(ezdxf.readfile(output))
    if remaining:
        print(f"仍残留占位符：{', '.join(sorted(remaining))}", file=sys.stderr)
        return 1
    print("复查通过：无残留占位符。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

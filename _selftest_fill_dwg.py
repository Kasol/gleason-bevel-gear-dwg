#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fill_dwg.py 自检：真实 DXF 往返 + 正负用例。

用法（用 DSH 运行时 python，系统 python 是 Store 桩）：
    <runtime>\\python.exe _selftest_fill_dwg.py

覆盖：
  T1  三种载体（TEXT / MTEXT / ATTRIB）回填，含重复占位符全部替换
  T2  回填后无 {{ 残留、非文字实体与图层不变
  T3  块定义内部文字不被替换（已知限制，断言其边界）
  T4  缺值：dry-run 返回 1，--write 拒绝写入且不产生输出文件
  T5  模板无占位符 → 1
  T6  参数文件非法 JSON → 2
  T7  模板不存在 → 2
  T8  不带模式参数时默认 dry-run，不落盘
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Windows 控制台默认 GBK，统一走 UTF-8，避免子进程输出被错误解码
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "scripts" / "fill_dwg.py"

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(ok), detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  <- ' + detail) if detail and not ok else ''}")


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd or HERE),
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
    )


def build_template(path: Path) -> None:
    """造一张含三类文字载体的模板。"""
    import ezdxf

    doc = ezdxf.new("R2018", setup=True)
    msp = doc.modelspace()

    # TEXT
    msp.add_text("模数 {{MT}}", dxfattribs={"height": 3.5}).set_placement((0, 0))
    # 重复占位符（参数表 + 标题栏场景）
    msp.add_text("重复 {{MT}}", dxfattribs={"height": 2.5}).set_placement((0, 8))
    # MTEXT（多行）
    msp.add_mtext("齿数 {{Z1}}\n精度 {{ACCURACY}}", dxfattribs={"char_height": 3.5}).set_location((0, 16))

    # 块属性 ATTRIB
    blk = doc.blocks.new("TITLE")
    blk.add_attdef("CASE", (0, 0), dxfattribs={"height": 2.5, "text": "{{CASE_DEPTH}}"})
    ref = msp.add_blockref("TITLE", (0, 30))
    ref.add_auto_attribs({"CASE": "{{CASE_DEPTH}}"})

    # 块定义内部文字：已知限制，不应被替换
    inner = doc.blocks.new("INNER")
    inner.add_text("{{SURFACE_HRC}}", dxfattribs={"height": 2.5})
    msp.add_blockref("INNER", (0, 40))

    # 非文字实体，用来验证回填不动图形
    msp.add_circle((50, 0), radius=10, dxfattribs={"layer": "0", "color": 3})
    msp.add_line((0, 0), (5, 5), dxfattribs={"layer": "0"})
    doc.saveas(path)


def layout_texts(path: Path) -> list[str]:
    import ezdxf

    doc = ezdxf.readfile(path)
    out: list[str] = []
    for layout in doc.layouts:
        for e in layout:
            t = e.dxftype()
            if t == "MTEXT":
                out.append(e.text)
            elif t == "TEXT":
                out.append(e.dxf.text)
            elif t == "INSERT":
                out.extend(a.dxf.text for a in e.attribs)
    return out


def entity_fingerprint(path: Path) -> list[str]:
    """实体类型 + 图层 + 颜色，用于确认回填没动图形。"""
    import ezdxf

    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    rows = []
    for e in msp:
        if e.dxftype() in ("TEXT", "MTEXT", "INSERT"):
            continue
        rows.append(f"{e.dxftype()}|{e.dxf.layer}|{getattr(e.dxf, 'color', 256)}")
    rows.append("LAYERS|" + ",".join(sorted(l.dxf.name for l in doc.layers)))
    return sorted(rows)


def main() -> int:
    if not SCRIPT.is_file():
        print(f"找不到脚本：{SCRIPT}")
        return 2
    import ezdxf

    print(f"ezdxf {ezdxf.__version__} / python {sys.version.split()[0]}")
    print(f"被测脚本：{SCRIPT}")

    with tempfile.TemporaryDirectory(prefix="filldwg-") as tmp:
        tmpdir = Path(tmp)
        tpl = tmpdir / "tpl.dxf"
        build_template(tpl)
        out = tmpdir / "out.dxf"

        good = {
            "MT": "5.0",
            "Z1": "23",
            "ACCURACY": "GB/T 11365 7级",
            "CASE_DEPTH": "0.8~1.2mm",
        }
        values = tmpdir / "values.json"
        values.write_text(json.dumps(good, ensure_ascii=False), encoding="utf-8")

        print("\n[T1/T2] 回填与复查")
        before_fp = entity_fingerprint(tpl)
        dry = run("--template", str(tpl), "--values", str(values), "--dry-run")
        check("dry-run 退出码 0", dry.returncode == 0, f"rc={dry.returncode} {dry.stderr.strip()[:200]}")
        check("dry-run 不落盘", not out.exists())
        check("dry-run 列出 4 种占位符", "占位符 4 种" in dry.stdout, dry.stdout[:200])
        check("dry-run 统计 5 处占位符", "共 5 处" in dry.stdout, dry.stdout[:200])

        wr = run("--template", str(tpl), "--values", str(values), "--write", "--out", str(out))
        check("--write 退出码 0", wr.returncode == 0, f"rc={wr.returncode} {wr.stderr.strip()[:200]}")
        check("输出文件已生成", out.is_file())
        check("输出含复查通过", "复查通过" in wr.stdout)
        # 脚本的"已回填 N 处"统计的是被修改的实体数（4 个），不是占位符个数（5 个）
        check("回填实体数 = 4", "已回填 4 处" in wr.stdout, wr.stdout[-200:])

        texts = layout_texts(out)
        joined = "\n".join(texts)
        check("无 {{ 残留", "{{" not in joined, joined[:200])
        check("TEXT 回填（模数 5.0）", "模数 5.0" in joined)
        check("重复占位符全替换", "重复 5.0" in joined)
        check("MTEXT 回填（齿数 23）", any("齿数 23" in t for t in texts))
        check("MTEXT 回填（精度）", any("GB/T 11365 7级" in t for t in texts))
        check("ATTRIB 回填（渗层）", "0.8~1.2mm" in texts)

        check("非文字实体与图层未变", entity_fingerprint(out) == before_fp,
              f"{entity_fingerprint(out)[:3]} != {before_fp[:3]}")

        print("\n[T3] 已知限制：块定义内部文字")
        doc_out = ezdxf.readfile(out)
        inner_text = [e.dxf.text for e in doc_out.blocks["INNER"] if e.dxftype() == "TEXT"]
        check("块定义内 {{SURFACE_HRC}} 未被替换（预期行为）",
              inner_text == ["{{SURFACE_HRC}}"], str(inner_text))
        check("该残留不会被残留检查发现（已知盲区）", "{{" not in joined)

        print("\n[T4] 缺值拦截")
        partial = tmpdir / "partial.json"
        partial.write_text(json.dumps({k: v for k, v in good.items() if k != "Z1"},
                                      ensure_ascii=False), encoding="utf-8")
        out2 = tmpdir / "should-not-exist.dxf"
        d2 = run("--template", str(tpl), "--values", str(partial), "--dry-run")
        check("dry-run 缺值返回 1", d2.returncode == 1, f"rc={d2.returncode}")
        check("缺值项被点名", "Z1" in d2.stdout + d2.stderr)
        w2 = run("--template", str(tpl), "--values", str(partial), "--write", "--out", str(out2))
        check("--write 缺值返回 1", w2.returncode == 1, f"rc={w2.returncode}")
        check("缺值时不产生输出文件", not out2.exists())

        print("\n[T5] 模板无占位符")
        plain = tmpdir / "plain.dxf"
        d = ezdxf.new("R2018")
        d.modelspace().add_text("空模板", dxfattribs={"height": 3.5})
        d.saveas(plain)
        r5 = run("--template", str(plain), "--values", str(values), "--dry-run")
        check("无占位符返回 1", r5.returncode == 1, f"rc={r5.returncode}")
        check("给出可辨识提示", "未发现" in r5.stdout, r5.stdout[:150])

        print("\n[T6] 参数文件非法 JSON")
        bad = tmpdir / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        r6 = run("--template", str(tpl), "--values", str(bad), "--dry-run")
        check("非法 JSON 返回 2", r6.returncode == 2, f"rc={r6.returncode}")

        print("\n[T7] 模板不存在")
        r7 = run("--template", str(tmpdir / "nope.dxf"), "--values", str(values), "--dry-run")
        check("模板缺失返回 2", r7.returncode == 2, f"rc={r7.returncode}")

        print("\n[T8] 不带模式参数默认 dry-run")
        out3 = tmpdir / "no-flag.dxf"
        r8 = run("--template", str(tpl), "--values", str(values), "--out", str(out3))
        check("默认不写盘", r8.returncode == 0 and not out3.exists(),
              f"rc={r8.returncode} exists={out3.exists()}")
        check("提示 dry-run", "[dry-run]" in r8.stdout, r8.stdout[-150:])

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n{'=' * 46}\n{passed}/{total} 通过")
    if passed != total:
        print("失败项：")
        for name, ok, detail in RESULTS:
            if not ok:
                print(f"  - {name}: {detail}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

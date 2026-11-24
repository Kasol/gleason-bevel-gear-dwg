# 格里森 / 等高齿锥齿轮成品图纸技能

把齿形参数、几何参数、技术要求回填进公司 DWG 成品模板，输出成品图纸 + 参数汇总 + 风险备注。
不做强度校核，不做工艺编制，不画新图框。

## 结构

```
gleason-bevel-gear-dwg/
├── SKILL.md                      # 入口：6 步串行流程 + 硬性约束
├── references/
│   ├── params.md                 # 19 项齿形参数 / 4 项几何参数 / 8 条自检判据
│   ├── tech-requirements.md      # 技术要求 5 条 + [S][F] 规则
│   └── template-and-output.md    # 模板约定 / 35 个占位符 / 输出话术 / 语言规则
├── scripts/
│   └── fill_dwg.py               # {{KEY}} 占位符回填（ezdxf）
├── .template/                    # 公司成品模板放这里（.dwg 优先，.dxf 次选）
└── _selftest_fill_dwg.py         # fill_dwg.py 自检：真实 DXF 往返 + 正负用例
```

## 快速验证

```powershell
# 依赖：ezdxf（Python 3.9+）
python scripts/fill_dwg.py --template 模板.dxf --values values.json --dry-run
python scripts/fill_dwg.py --template 模板.dxf --values values.json --write --out 成品.dxf

# 自检（27 条断言）
python _selftest_fill_dwg.py
```

`values.json` 的 key 不带花括号，取值一律字符串：

```json
{"MT": "5.0", "Z1": "23", "ACCURACY": "GB/T 11365 7级", "CASE_DEPTH": "0.8~1.2mm"}
```

退出码：`0` 成功且无残留；`1` 有缺值或残留占位符；`2` 文件/参数错误。

## 安装到本地技能目录

本仓库是**源**，改完同步到 DSH 的技能目录：

```powershell
Copy-Item -Recurse -Force .\* "$env:USERPROFILE\.agents\skills\gleason-bevel-gear-dwg\"
```

## 当前状态与已知缺口

已实现：占位符扫描、回填、残留复查、dry-run、正负用例自检（27/27）。

仍未打通：

1. **没有 DWG 工具链** —— 脚本只认 DXF。DWG 需先用 ODA File Converter 转换，回填后再转回；本机尚未安装任何转换器。
2. **没有图纸解析 MCP** —— 流程第 3 步"从客户图纸提取内孔直径/最大外径/安装距/模数"无法自动执行，只能走手填降级路径。
3. **`.template/` 无真实模板** —— 第 4 步会按设计停止。

已知盲区（`fill_dwg.py`）：

- **块定义内部**的 `{{...}}` 不会被替换，且残留复查**也扫不到**——若模板把参数表做成块，会打印"复查通过"但图上仍留占位符。
- `ACAD_TABLE`（表格实体）的单元格文字不在扫描范围内（推断，待真模板验证）。

## 设计约束（改之前先读）

- 齿制闸门放第一位，只回一句话术，不解释、不建议替代方案
- 参数冲突只报不改，绝不替用户选值
- 用户手填值优先于 MCP 识别值，差异写风险备注
- 不许用默认值填必填项
- 技术要求 5 条逐字不可改，只替换占位字段
- `[S]` 只绑渗碳淬火条款，`[F]` 只绑精度等级所在行
- 偏置距 ≠ 0 必须转准双曲面拦截（`tan δ = z1/z2` 只在轴交角 90° 普通锥齿轮下成立）
- 模板基底固定不可改，模板缺失就停止，不许从零绘制

# 格里森 / 等高齿锥齿轮成品图纸技能

把齿形参数、几何参数、技术要求回填进公司 DWG 成品模板，输出成品图纸 + 参数汇总 + 风险备注。
不做强度校核，不做工艺编制，不画新图框。

> **AI 智能体**：直接跳到 [给 AI 智能体的自助安装](#给-ai-智能体的自助安装)，按第 1–6 步执行，装完回报自检结果。
> **人类读者**：见 [人工使用](#人工使用)。

## 这是一个通用 skill

不绑定任何单一智能体平台，形态遵循 Agent Skills 约定，可以被任何"能读文件 + 能跑命令"的宿主安装：

- 入口是 `SKILL.md`（YAML frontmatter + Markdown 正文），其余是 `references/`、`scripts/`、`.template/`
- 无安装包、无构建步骤、无服务端、无网络调用、无宿主专有配置
- 目录内部一律相对路径引用，整目录移动到哪都能工作
- 唯一运行时依赖：Python 3.9+ 与 `ezdxf`（纯 Python，Windows / Linux / macOS 同构）
- 仓库名 = 技能名 = frontmatter `name`，因此**克隆到技能目录即完成安装**

| 宿主 | 读取位置 |
|---|---|
| Claude Code / Claude Agent SDK | `~/.claude/skills/<name>/`（个人）或 `<项目>/.claude/skills/<name>/` |
| Codex CLI | `~/.codex/skills/<name>/` |
| DSH 及其它跨工具宿主 | `~/.agents/skills/<name>/` |
| 无技能机制的宿主（Cursor / Cline / Copilot Chat / 自研 agent） | 降级：写进 `AGENTS.md` 等指令文件 |

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

---

## 给 AI 智能体的自助安装

> 本节是写给 AI 智能体执行的。你可能是 Claude Code、Codex CLI、Cursor、Cline、DSH 或任何其它宿主。
> 本节**不假定宿主类型**，按下面 6 步走即可；判定不了宿主时走第 5 步的降级路径。

### 第 0 步 认清你要装的是什么

一个**纯文件目录**。安装 = 复制/克隆一个目录，卸载 = 删掉那个目录。不存在注册表、服务、全局状态。
所以任何"安装失败"只可能是三类原因：路径不对、依赖没装、目录被套成两层。

### 第 1 步 判定安装位置

从上往下匹配，命中即停：

| 判定依据 | 安装到 |
|---|---|
| 宿主是 Claude Code（有 `~/.claude` 或 `.claude/`，文档提到 skills） | `~/.claude/skills/gleason-bevel-gear-dwg/` |
| 宿主是 Codex CLI（有 `~/.codex`） | `~/.codex/skills/gleason-bevel-gear-dwg/` |
| 宿主读取 `~/.agents/skills`（跨工具约定，DSH 等） | `~/.agents/skills/gleason-bevel-gear-dwg/` |
| 只为当前项目服务，且宿主支持项目级技能 | `<项目>/.claude/skills/` 或 `<项目>/.agents/skills/` 下的同名目录 |
| 都不是 / 无法判定 | 跳到第 5 步 |

判定不了就同时装 `~/.claude/skills` 与 `~/.agents/skills`：目录是纯文本、体积几十 KB，重复安装无害。
但**同一个宿主内不要留两份同名不同版本**，否则技能清单里会出现重复项。

### 第 2 步 取代码

```bash
git clone https://github.com/Kasol/gleason-bevel-gear-dwg.git
```

已经在本机（比如就在当前工作目录里）就跳过这步，直接用现有路径。

### 第 3 步 放到技能目录（目录名必须保持 `gleason-bevel-gear-dwg`）

克隆即安装——把目标路径直接作为 clone 目录：

```bash
# bash / zsh / Git Bash
git clone https://github.com/Kasol/gleason-bevel-gear-dwg.git ~/.claude/skills/gleason-bevel-gear-dwg
```

```powershell
# PowerShell
$dst = Join-Path $HOME '.claude\skills\gleason-bevel-gear-dwg'
git clone https://github.com/Kasol/gleason-bevel-gear-dwg.git $dst
```

已经有本地副本时改为复制（**复制目录本身，不要复制目录内容**）：

```bash
cp -r ./gleason-bevel-gear-dwg ~/.claude/skills/gleason-bevel-gear-dwg
```

```powershell
Copy-Item -Recurse -Force .\gleason-bevel-gear-dwg (Join-Path $HOME '.claude\skills\gleason-bevel-gear-dwg')
```

> 常见错误：装成 `skills/gleason-bevel-gear-dwg/gleason-bevel-gear-dwg/`。自检能过，但宿主扫不到 `SKILL.md`。
> 装完必须确认目标目录下**直接**有 `SKILL.md`。

### 第 4 步 自检（不要跳过）

```bash
cd ~/.claude/skills/gleason-bevel-gear-dwg
python3 _selftest_fill_dwg.py   # Windows 上用 python 或指定解释器绝对路径
```

判据：

- 输出 `27/27 通过`，退出码 `0` → 安装成功
- 报 `ModuleNotFoundError: ezdxf` → 先 `pip install ezdxf` 再重跑（依赖装进解释器环境，**不要**装进技能目录）
- 报 `找不到脚本` → 目录套了两层，回到第 3 步

**自检没通过就不要告诉用户"已安装"。** 最多说"文件已放置，但自检未通过"，并附报错原文。

### 第 5 步 宿主没有技能机制时（降级）

把下面这段追加到宿主的指令文件——`AGENTS.md`、`CLAUDE.md`、`.github/copilot-instructions.md`、`.cursor/rules/*.mdc` 等，任选宿主实际读取的那个：

```markdown
## 可用技能：gleason-bevel-gear-dwg

需要生成格里森 / 等高齿锥齿轮成品 DWG 图纸（或用户要求"按锥齿轮参数出成品图"、
"套用 DWG 模板生成锥齿轮图纸"）时，先完整读取
<这里写绝对路径>/SKILL.md，再严格按其 6 步串行流程执行。
SKILL.md 中引用的 references/、scripts/、.template/ 均相对该文件所在目录解析。
仅限锥齿轮成品图；圆柱齿轮、链轮、花键、毛坯图、工装图、工序卡不适用。
```

`<这里写绝对路径>` 换成真实路径（如 `D:/skills/gleason-bevel-gear-dwg`），别留占位符。

### 第 6 步 回报用户

安装完成后按这三行回报，不要只回"装好了"：

1. **安装位置**：实际路径（绝对路径）
2. **自检结果**：`27/27 通过` 或报错原文
3. **能力边界**：技能已就绪，但 `.template/` 为空、本机无 DWG 转换工具、无图纸解析 MCP —— 因此在放入真实模板前，它会按设计停在第 4 步，这是预期行为，不是 bug

### 验收标准（4 条全满足才算装好）

1. `<目标目录>/SKILL.md` 存在，首行是 `---`
2. 6 个技能文件齐全：`SKILL.md`、`references/{params,tech-requirements,template-and-output}.md`、`scripts/fill_dwg.py`、`.template/README.md`
3. `_selftest_fill_dwg.py` 跑出 `27/27`
4. 新开一个会话后，宿主能在技能清单里列出 `gleason-bevel-gear-dwg`（宿主若无"技能清单"概念，跳过此条）

### 不要做的事

- 不要为了"适配宿主"去改 `SKILL.md` / `references/` 的内容（要适配就在宿主侧加包装，技能本身保持中立）
- 不要删除或替换 `.template/` 里的文件
- 不要把本仓库装成宿主安装目录的子目录（如 `node_modules/`、`site-packages/`）
- 不要跳过自检，也不要在自检失败时声称安装完成
- 不要在没有真实模板时承诺"能出图"——技能第 4 步会直接停止
- 不要假定 Windows：脚本用 `pathlib`，Linux / macOS 同样可跑

### 环境依赖

| 依赖 | 要求 | 说明 |
|---|---|---|
| Python | 3.9+ | 只用标准库 + ezdxf |
| ezdxf | 1.3+（实测 1.4.5） | `pip install ezdxf`，仅 DXF 读写 |
| DWG 转换器 | 可选 | 无 ODA File Converter / AutoCAD 时只支持 DXF 输入输出 |

---

## 人工使用

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

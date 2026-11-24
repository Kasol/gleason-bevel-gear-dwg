# 格里森 / 等高齿锥齿轮成品图纸技能

把齿形参数、几何参数、技术要求回填进公司 DWG 成品模板，输出成品图纸 + 参数汇总 + 风险备注。
不做强度校核，不做工艺编制，不画新图框。

> **AI 智能体**：读 [给 AI 智能体的接入说明](#给-ai-智能体的接入说明)，先选通道再动手。不要跳过通道选择直接复制路径。
> **人类读者**：见 [人工使用](#人工使用)。

## 这是一个通用 skill

本仓库不绑定任何单一智能体平台。它在技术上满足的条件是：

- 形态遵循 Agent Skills 约定：一个目录 + `SKILL.md`（YAML frontmatter + Markdown 正文）+ 可选的 `references/`、`scripts/`、`assets/`
- 无安装包、无构建步骤、无服务端、无网络调用、无宿主专有配置、不读写宿主注册表或全局状态
- 目录内部一律相对路径引用，整目录移动到哪都能工作
- 唯一运行时依赖：Python 3.9+ 与 `ezdxf`（纯 Python，Windows / Linux / macOS 同构）
- 仓库名 = 技能名 = frontmatter `name`，因此把仓库整体放到宿主的技能位置即可（见下文通道 A）

宿主如何"接入"这个目录，各平台并不统一。下节按能力而不是按平台名来描述接入方式。

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

## 给 AI 智能体的接入说明

> 本节写给 AI 智能体。你可能是 Claude Code、Codex CLI、Cursor、Cline、DSH、某个内部 agent 框架，也可能只是一个能读文件的一次性会话。
> 本节**不假定宿主**：不假定你有"技能目录"，不假定这个目录叫什么，不假定你跑在 Windows 上。

### 目标不是"复制到某个路径"

目标是：**当用户提出锥齿轮出图需求时，你的宿主能读到 `SKILL.md` 并按它的 6 步流程执行。**

路径只是达成这个目标的一种手段，而且是所有手段里最宿主相关的一种。所以先选手段，再谈路径。

### 三条接入通道，按保真度从高到低

| 通道 | 适用情况 | 你要做的事 | 保真度 |
|---|---|---|---|
| **A 原生技能机制** | 宿主有 skills 概念（扫目录、读清单、或插件式加载） | 把本目录放到宿主加载 skills 的位置 | 最高：可自动发现、按 `description` 触发 |
| **B 指令文件** | 宿主启动时读项目级/用户级指令文件（`AGENTS.md`、`CLAUDE.md`、规则目录等） | 在指令文件里加一段引用，指向 `SKILL.md` 的真实路径 | 中：靠指令文字命中，不会被自动索引 |
| **C 会话注入** | 一次性会话、无持久化目录、或 A/B 都不可用 | 直接读 `SKILL.md` 全文进上下文，按它执行 | 最低，但永远可用 |

选择顺序：**能 A 就 A，不行退 B，再不行用 C。** 你选了哪条、装到哪里，必须告诉用户（见"回报"）。

### 通道 A：先找位置，别猜

按顺序执行，命中即停：

1. **查宿主自己的说明**（最可靠）。宿主若支持 skills，文档或配置里会写加载目录 / 注册方式。有就照它做，本文档不作数。
2. **探测本机已有的技能目录**（不假定具体名字）：

   ```bash
   # 列出 $HOME 下三层内名为 skills / skill 的目录（任何宿主都适用）
   find "$HOME" -maxdepth 3 -type d \( -name skills -o -name skill \) 2>/dev/null
   ```

   ```powershell
   # PowerShell 等价
   Get-ChildItem $HOME -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object {
     Get-ChildItem $_.FullName -Directory -Force -ErrorAction SilentlyContinue |
       Where-Object { $_.Name -in @('skills','skill') }
   } | Select-Object -ExpandProperty FullName
   ```

   判断依据：探到的目录里若已存在 `<某个名字>/SKILL.md` 形态的兄弟目录，这个目录基本就是对的。
3. **问用户**。探测不到、或探到多个彼此矛盾时，直接问："你的智能体从哪里加载技能？"。**不要挑一个最像的硬装。**

拿到位置后，把本仓库整体放成 `<SKILLS_DIR>/gleason-bevel-gear-dwg/`：

```bash
# 目标目录已知时；<SKILLS_DIR> 是你上一步探测或问到的真实路径，不是示例
git clone https://github.com/Kasol/gleason-bevel-gear-dwg.git "<SKILLS_DIR>/gleason-bevel-gear-dwg"
```

```powershell
git clone https://github.com/Kasol/gleason-bevel-gear-dwg.git "$SKILLS_DIR\gleason-bevel-gear-dwg"
```

已经有本地副本时改为复制**目录本身**（不是目录内容）：

```bash
cp -r ./gleason-bevel-gear-dwg "<SKILLS_DIR>/gleason-bevel-gear-dwg"
```

两个硬性要求：

- **目录名保持 `gleason-bevel-gear-dwg`**（与 frontmatter `name` 一致）
- **目标目录下必须直接有 `SKILL.md`**。装成 `.../gleason-bevel-gear-dwg/gleason-bevel-gear-dwg/SKILL.md` 时自检会过，但宿主扫不到，这是最常见的失败

> **已知的一些实现**（仅作为第 2 步的判断线索，**不是默认值**，也不构成清单）：
> `~/.claude/skills`、`~/.codex/skills`、`~/.agents/skills` 这几个位置在某些宿主上是技能目录。
> 你的宿主不在这几个里，就说明它用的是别的位置——继续探测或问用户，不要为了"对上号"硬装到一个不相关的地方。

### 通道 B：宿主没有技能目录时

找到宿主实际读取的指令文件——常见形态是项目根或用户目录下的 `AGENTS.md`、`CLAUDE.md`、`.github/copilot-instructions.md`、规则目录里的 Markdown（如 `.cursor/rules/*.mdc`）——把下面这段追加进去：

```markdown
## 可用技能：gleason-bevel-gear-dwg

需要生成格里森 / 等高齿锥齿轮成品 DWG 图纸时（用户说"按锥齿轮参数出成品图"、
"套用 DWG 模板生成锥齿轮图纸"、"输入齿形参数和技术要求出图纸"等），
先完整读取 <SKILL_DIR>/SKILL.md，再严格按其 6 步串行流程执行。

SKILL.md 中引用的 references/、scripts/、.template/ 均相对该文件所在目录解析，
不要按当前工作目录解析。本技能仅限锥齿轮成品图；圆柱齿轮、链轮、花键、
毛坯图、工装图、工序卡不适用。
```

`<SKILL_DIR>` 换成技能目录的绝对路径。**写绝对路径，且写完要验证它真的能解析到 `SKILL.md`**——留占位符或写相对路径，等于没接。

### 通道 C：什么持久化机制都没有时

直接把 `SKILL.md` 全文读进上下文，然后按它执行：

- `SKILL.md` 是唯一入口，6 步流程和硬性约束都在里面
- 需要细节时再按其中的相对路径读 `references/*.md`
- `references/` 不必预先全读，按需加载即可（这也是它被拆成三个文件的原因）
- 通道 C 下每次新会话都要重新注入，所以要告诉用户这个事实

### 三个通道都要做的自检

自检脚本用**自身位置**定位被测文件，与当前工作目录无关，可从任意路径调用：

```bash
python3 "<技能目录>/_selftest_fill_dwg.py"
```

```powershell
python "$技能目录\_selftest_fill_dwg.py"
```

判据：

- 输出 `27/27 通过`、退出码 `0` → 可用
- `ModuleNotFoundError: ezdxf` → 先 `pip install ezdxf` 再重跑。依赖装在解释器环境，**不要**装进技能目录
- `找不到脚本` → 目录套了两层或路径写错，回到通道 A 的层级检查

**自检没通过就不要告诉用户"已装好"。** 最多说"文件已放置，但自检未通过"，并附报错原文。

### 回报用户（三行，缺一不可）

1. **接入方式**：走的哪条通道（A/B/C），以及具体位置或指令文件路径
2. **自检结果**：`27/27 通过`，或报错原文
3. **能力边界**：技能已就绪 ≠ 能出图。`.template/` 为空、本机无 DWG 转换器、无图纸解析 MCP 时，它会在第 4 步停下——这是设计行为，不是安装失败

### 验收标准（4 条全满足才算接好）

1. 宿主确实能读到 `SKILL.md`（A：技能目录顶层就是它；B：指令文件里的路径能解析到真实文件；C：已读入上下文）
2. 6 个技能文件齐全：`SKILL.md`、`references/{params,tech-requirements,template-and-output}.md`、`scripts/fill_dwg.py`、`.template/README.md`
3. 自检跑出 `27/27`
4. 用一句真实需求试一次（如"按这些参数出一张格里森锥齿轮成品图"），确认能进入 `SKILL.md` 第 1 步。进不去就说明通道选错或路径写错，回去重选

### 不要做的事

- **不要照抄本文里的示例路径**。`~/.claude/skills` 之类只是举例，正确路径必须来自探测或用户告知
- **不要用未替换的 `<SKILLS_DIR>` / `<SKILL_DIR>` 占位符执行命令**，那样只会装到一个叫这个名字的垃圾目录
- 不要为了"适配宿主"去改 `SKILL.md` / `references/` 的内容（要适配就在宿主侧加包装，技能本身保持中立）
- 不要删除或替换 `.template/` 里的文件（`.template/README.md` 还承担着让 git 保留这个目录的作用，删了克隆下来目录就不存在）
- 不要把本仓库装进宿主自己的安装目录（`node_modules/`、`site-packages/` 等）
- 不要跳过自检，也不要在自检失败时声称安装完成
- 不要在没有真实模板时承诺"能出图"——技能第 4 步会直接停止
- 不要假定 Windows：脚本用 `pathlib`，Linux / macOS 同样可跑；本文命令给了 bash 与 PowerShell 两版

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

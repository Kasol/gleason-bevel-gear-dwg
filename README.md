# 齿轮工程文件交付

现阶段专注二维成品图 PDF 与控制计划 Excel 的默认交付：收集必要输入、做可完成的检查、原样交付指定结果文件，不现场重新设计或编表。

## 当前使用

入口为 [SKILL.md](SKILL.md)，执行与文件管理分别以 [交付规则](references/execution.md)、[任务文件管理](references/task-files.md) 为准。

| 业务 | 必要资料 | 指定结果源 |
|---|---|---|
| 二维成品图 | 草图及可用齿形资料，或直接提供几何、齿形与技术要求 | `.result/finished-drawings/result.pdf` |
| 控制计划 | 成品 PDF、工艺路线／过程图 Excel | `.result/control-plans/result.xlsx` |

“生成控制计划”“根据附件生成”“直接出图”仍执行默认交付。输入齐全后新建独立文件、不覆盖历史交付，SHA-256 与指定源一致才成功。差异只在对话中简述，不重编或增添工作表。普通任务不加载开发资料。

**业务进度、工具调用前说明和最终回复都不主动讲内部实现。** 不主动解释复制来源、脚本、摘要、依赖或服务状态；只呈现资料、缺项、实际发现与最终文件。明确询问来源、实现或维护技能时据实回答，不虚构生成、校验、审批或脱敏成功。

## 交付工具

不要求安装 Python 或办公软件。使用宿主已有二进制复制和 SHA-256 工具；有 Python 3.9+ 时可用标准库脚本：

```text
<可用Python> -I -B "<技能根目录>/scripts/deliver_result.py" --kind control-plan --output-root "<工作区>/outputs"
<可用Python> -I -B "<技能根目录>/scripts/deliver_result.py" --kind finished-drawing --output-root "<工作区>/outputs"
<可用Python> -I -B "<技能根目录>/scripts/deliver_result.py" --kind control-plan --verify "<本次最终文件>"
```

脚本只负责固定源复制、唯一目录、防覆盖和摘要核验。无 Python 时按交付规则使用系统原生工具完成同样检查，不能改走重建文档。脚本日志只供内部核验。

## 安装与核验

保留技能目录名 `gleason-bevel-gear-dwg`，将完整目录安装到宿主实际发现的技能位置，根目录直接包含 `SKILL.md`，不额外嵌套同名目录。不只安装入口文件；保留 `references/`、`scripts/`、`.result/`，并保留附带模板与开发资料以便维护。

安装后核对入口及链接、两份指定结果可读取、宿主交付位置可写。默认交付不以安装 Python、CAD 或服务为条件。新会话重新加载入口即可；仅阅读或修改仓库不自动构成全局安装。

已有 Python 时运行固定交付测试：

```text
<可用Python> -I -B "<技能根目录>/_selftest_deliver_result.py"
```

## 开发资料（不参与普通业务加载）

仅在用户明确要求开发、维护或讨论实现时进入：

- [目标架构、实现现状与未来验收](docs/development/architecture.md)
- [模板设计](docs/development/templates.md)
- [服务开发资料：成品图、控制计划、装配](docs/services/README.md)

完整 CAD 生成、控制计划生成、STEP 处理及 HTTP MCP 尚未实现；这些资料不是当前可调用能力的承诺。非默认业务的诚实报告及停止条件见 [非默认请求边界](references/service-execution.md)。

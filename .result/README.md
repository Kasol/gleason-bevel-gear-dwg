# 云端交付资源

本目录仅保留 JSON 资源配置，不存放 PDF／Excel 二进制文件，以免 SkillHub 导入时过滤结果资产。配置只读使用；按 [交付规则](../references/execution.md) 下载并核验为本次新文件，只链接新交付文件。目录和临时文件清理见 [任务文件管理](../references/task-files.md)。

| 结果 | 资源配置 | `kind` | 云端文件名 |
|---|---|---|---|
| 二维成品图 | [finished-drawings/resources.json](finished-drawings/resources.json) | `finished-drawing` | `engine-drawing.pdf` |
| 控制计划表 | [control-plans/resources.json](control-plans/resources.json) | `control-plan` | `control-plan.xlsx` |
| 非标件 1 | [mate/resources.json](mate/resources.json) | `custom-part1` | `custom-part1.pdf` |
| 非标件 2 | [mate/resources.json](mate/resources.json) | `custom-part2` | `custom-part2.pdf` |
| 非标件 3 | [mate/resources.json](mate/resources.json) | `custom-part3` | `custom-part3.pdf` |

五项资源均位于 `https://kasol-store-1251959208.cos.ap-shanghai.myqcloud.com/`，每项的完整地址写在 JSON 中。下载需要宿主可访问该域名，无需云账号密钥。二维成品图和控制计划在必要输入齐全后当轮交付；参数检查失败或信息差异不增加确认步骤。`mate` 表示第三阶段的装配相关结果，目前仅配置三个非标件 PDF，不表示已提供装配分析、干涉检查或实际出图服务。

## 配置格式

每个配置使用 `schema_version: 1`，`files` 以脚本的 `kind` 为键：

- `url`：文件的完整 HTTPS 下载地址。
- `filename`：本次交付使用的文件名，不含目录。
- `size_bytes`：已确认源文件的字节数。
- `sha256`：已确认源文件的 64 位小写 SHA-256。

下载直接写入技能目录外的唯一任务目录，大小和 SHA-256 都一致才成功；不修改文档、不生成额外清单或缓存。下载失败、文件变动或摘要不符时清理本次半成品，不能自动信任新内容或改写配置绕过校验。只读核验已有交付文件时无需重新下载。

维护人员更换云端文件时，应确认新内容并同步更新 URL、字节数和 SHA-256；不要只覆盖同名云文件而保留旧摘要。新增资源时还需同步脚本中的 `RESULTS` 映射与相关说明。可用 `_selftest_deliver_result.py --online` 核验全部实际资源，临时测试产物自动清理。

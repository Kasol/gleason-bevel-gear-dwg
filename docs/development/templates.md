# 模板设计与 DXF 辅助脚本

仅开发、维护或实现讨论时读取，不参与默认文件交付。资产清单见 [模板目录](../../.template/README.md)，成品图的详细规则见 [模板与输出设计](../services/template-and-output.md)。

## 模板设计

同类零件参数化模板需明确：

- 可变轮廓、结构尺寸、几何依赖、标注及允许范围。
- 几何、齿形参数表及技术条款的字段映射。
- 上下偏差、基准、S／F 标记的绑定与展示。
- 图框、图层、标注样式及 PDF 图面要求。
- 身份脱敏字段和保留制造数据的检查要求。

不能凭文件名判定模板角色或适用性；多个候选按明确引用选择。`.template/control-plans/typical.xlsx` 是历史样例，其具体数值不作默认输入。非标件图纸模板和目标样例尚待提供。版本及后端设计见 [架构资料](architecture.md)。

## 已有 DXF 文字回填

Python 3.9+、ezdxf 1.3+；依赖不放入技能目录。以下路径相对技能根目录，执行时传入实际路径：

```text
<可用Python> -I -B "<技能根目录>/scripts/fill_dwg.py" --template "<模板.dxf>" --values "<values.json>" --dry-run
<可用Python> -I -B "<技能根目录>/scripts/fill_dwg.py" --template "<模板.dxf>" --values "<values.json>" --write --out "<新结果.dxf>"
<可用Python> "<技能根目录>/_selftest_fill_dwg.py"
```

`values.json` 是旧文字字典接口，不是完整业务协议；key 不带花括号，值为已格式化字符串，例如：

```json
{"MT": "5.0", "Z1": "23", "ACCURACY": "GB/T 11365 7级", "CASE_DEPTH": "0.8~1.2mm"}
```

脚本仅替换 DXF 布局 TEXT／MTEXT 及 INSERT 属性的 `{{KEY}}`，不修改几何、尺寸标注、图层或布局，不做 PDF 导出或脱敏。DWG 转换须另有实际可用工具。

默认 dry-run 不写文件，缺值拒绝写入；退出码 0 代表自身扫描范围无缺值或残留，1 代表缺值、残留或无占位符，2 代表已处理的文件／参数错误，其他读取异常可能抛出。不遍历块定义内部文字及表格单元格，残留检查也存在同样盲区，不自动炸开业务模板。现有 27 项自检断言包含此盲区的确认，通过不代表完整出图能力可用。

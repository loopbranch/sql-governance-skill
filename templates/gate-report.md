# SQL 门禁检视报告

## 范围

- 基线：`<commit/ref>`
- 目标：`<commit/ref>`
- 检查文件：`<数量与路径>`
- SQL 入口：`<.sql / migration / ORM / inline SQL>`
- 规则版本：`<tag + commit>`

## 门禁结论

`FAIL (Block) | PASS WITH WARNINGS | PASS | NOT TRIGGERED`

- Block：`<n>`
- Warn：`<n>`
- Info：`<n>`
- Confirmation required：`<n>`

## 发现项

### `<层级> <规则 ID> <简短标题>`

- 文件：`path/to/file.sql:<1-based line>`
- 片段：`<最小必要片段，注意脱敏>`
- 原文条款：`<G....>`
- 判定：`<静态命中 / 人工证据缺失 / 例外无效>`
- 风险：`<影响>`
- 整改：`<可执行的最小修复>`
- 状态：`open | fixed | confirmation-required | exception`
- 证据：`<diff/EXPLAIN/批准记录链接>`

## 已确认但仍需独立检验的变更

| 变更 | 确认结论 | 确认证据 | 规则合规结论 |
|---|---|---|---|
| `<内容>` | `确认` | `<链接/记录>` | `<Pass/Block>` |

## 检查限制

- `<未获得 schema、真实基数、生产配置或执行计划等>`

Block 大于 0 或存在 `confirmation-required` 时，提交/PR/CodeCheck 门禁必须失败。

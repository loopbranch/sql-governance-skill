# 分层、门禁与判定模型

| 规范层级 | 含义 | 门禁 | 处理方式 |
|---|---|---|---|
| `prohibition` 禁止 | 明确禁止的行为 | Block | 必须修复；确认不能豁免 |
| `mandatory` 强制 | 明确“必须/需要/不允许”的要求 | Block | 缺失即失败；补齐证据或实现 |
| `recommendation` 建议 | “建议/应/避免/不宜”等优化要求 | Warn | 给出风险与优化建议；不单独阻断 |
| `reference` 参考 | 背景、示例、可选实践 | Info | 提示，不要求整改 |

## 判定能力

- `static`：仅凭当前代码/SQL 可稳定判定，且已由仓库静态门禁实现；实际自动覆盖清单见 `rules/README.md` 和 JSON 输出的 `checked_rules`。
- `manual`：依赖业务语义、数据规模、运行时统计、审批或执行窗口；必须列出所需证据。
- `hybrid`：静态发现候选问题，再由 schema、EXPLAIN、业务上下文或批准记录定论。

发现结构性变更或大批量数据变更时，无论规则最终是 Block、Warn 还是 Info，均先进入开发者确认流程。确认只授权继续处理已描述的方案，不改变规则层级，也不授权执行生产 SQL。

## 结果状态

- `pass`：适用 Block 均已验证通过，Warn/Info 已记录。
- `fail`：存在任一未整改 Block。
- `confirmation-required`：需要人工确认但确认缺失、模糊、过期或与当前范围不一致；按 Block 处理。
- `dialect-required`：无法确认 MySQL 或 PostgreSQL；只可报告公共规则，方言合规结论按 Block 处理。
- `not-applicable`：有证据表明规则不适用。
- `exception`：仅当规则允许例外，且批准范围、理由、批准人/角色、有效期和链接齐全。
- `normal-rollback`：可信测试证明同批升级和回滚后结构、数据恢复，且逆操作精确匹配已执行脚本。按适用方言完成语法验证后，该操作不计入破坏性变更 Block。

报告中的总门禁结论按最严重项聚合：Block（含 confirmation-required、dialect-required） > Warn > Info > Pass。

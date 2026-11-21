# Changelog

遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added

- 预留后续规则与检测器变更。

## [1.0.0] - 2026-11-21

### Added

- 首版 SQL Governance SKILL，覆盖方案期与代码门禁两个触发场景。
- 四层规范模型与 Block/Warn/Info 门禁映射。
- 结构性变更和大批量数据变更的显式开发者确认机制。
- 24 条机器可读示例规则，覆盖命名、格式、建表、字段、索引、DML、事务、性能、升级、安全和归档。
- 方案期意见、门禁检视和开发者确认模板。
- git submodule 引入、克隆、升级、锁定、回退及多仓库一致性说明。
- 规则目录校验脚本，以及可对高置信 Block 返回非零退出码的静态 SQL 门禁脚本；均无第三方依赖。

[Unreleased]: https://github.com/loopbranch/sql-governance-skill/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/loopbranch/sql-governance-skill/releases/tag/v1.0.0

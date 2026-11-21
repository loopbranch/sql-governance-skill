# Git submodule 集成、同步与版本策略

公共仓库地址为 `https://github.com/loopbranch/sql-governance-skill.git`，以下用主工程路径 `.skills/sql-governance` 举例。不要在多个主工程复制 `rules/`。

## 首次引入

```bash
git submodule add https://github.com/loopbranch/sql-governance-skill.git .skills/sql-governance
git add .gitmodules .skills/sql-governance
git commit -m "chore: 引入 SQL 公共规则"
```

建议在 `.gitmodules` 明确跟踪稳定分支，便于“查询上游最新版本”，但主工程实际仍锁定 commit：

```ini
[submodule ".skills/sql-governance"]
    path = .skills/sql-governance
    url = https://github.com/loopbranch/sql-governance-skill.git
    branch = main
```

## 克隆主工程

一次完成：

```bash
git clone --recurse-submodules <main-repo-url>
```

已普通克隆时：

```bash
git submodule update --init --recursive
```

检出主工程的历史提交或切换分支后，运行同一条 `update --init --recursive`，使 submodule 回到该主工程提交记录的精确 commit。

## 上游更新与显式升级

规则仓库先通过 PR 合并，更新 `CHANGELOG.md`，创建语义化 tag（如 `v1.2.0`）。每个主工程再单独发升级 PR：

```bash
git submodule update --remote .skills/sql-governance
git -C .skills/sql-governance describe --tags --always
git -C .skills/sql-governance log -1 --oneline
git diff --submodule=log -- .skills/sql-governance
git add .skills/sql-governance
git commit -m "chore: 升级 SQL 规则至 v1.2.0"
```

`git submodule update --remote` 只把工作区移动到配置分支的最新上游 commit；只有提交主工程中的 gitlink 变化，团队才真正锁定并共享该版本。

若要严格锁定已评审 tag 对应的 commit：

```bash
git -C .skills/sql-governance fetch --tags
git -C .skills/sql-governance checkout v1.2.0
git add .skills/sql-governance
git commit -m "chore: 锁定 SQL 规则 v1.2.0"
```

## 升级 PR 必查

- `CHANGELOG.md` 中当前版本到目标版本的全部变更；
- `git diff --submodule=log` 展示的 commit 范围；
- 新增/升级的 Block 是否会影响存量迁移、门禁和开发流程；
- `python3 .skills/sql-governance/scripts/validate_rules.py`；
- 在主工程代表性 SQL 差异上试运行/人工回归，记录新增告警和处理结论；
- PR 描述记录旧 commit/tag、新 commit/tag、规则差异、回退方式和评审人。

回退时把 submodule checkout 到先前已知良好的 commit，再提交主工程 gitlink 回退。不要删除或改写上游 tag。

## 多仓库一致性保障

- 唯一事实来源：只有公共规则仓库可修改规则；主工程 submodule 目录视为只读。
- 精确锁定：主工程 Git 记录 submodule commit，不依赖浮动分支或运行时自动拉取。
- 显式升级：禁止 CI、启动脚本或开发工具自动执行 `update --remote` 并提交；升级必须是可审查 PR。
- 版本台账：各主工程可在依赖清单记录 `<主工程, 规则 tag, commit, 升级 PR>`，但不复制规则内容。
- 一致性检查：CI 只验证 submodule 已初始化、工作树干净、commit 在允许的已签名 release/tag 集合中；不得静默改到最新版本。
- 批量升级：可由机器人分别创建 PR，但每个仓库仍独立评审和合并，不能绕过锁定。

## 版本发布

采用 SemVer `vX.Y.Z`：破坏性门禁变化升 MAJOR，兼容新增规则/能力升 MINOR，不改变门禁语义的修复升 PATCH。每次发布：规则 PR -> 校验 -> 更新 CHANGELOG -> 合并 -> 签名 tag -> GitHub Release。禁止移动或复用已发布 tag。

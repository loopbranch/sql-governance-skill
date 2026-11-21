# 规则库约定

`catalog.json` 是规则路由清单，`common.json` 保存附件 154 个编号条款的公共抽象，`mysql.json` 与 `postgresql.json` 分别保存方言差异。`schema.json` 定义规则文件格式。模板和 `SKILL.md` 只引用规则，不复制规则正文。

加载顺序固定为：

- MySQL：`common.json` → `mysql.json`；
- PostgreSQL：`common.json` → `postgresql.json`。

方言文件只能收紧、澄清或替换具体语法，不得静默取消公共 Block。公共规则中的编码、表实现、时间类型、UUID、在线 DDL 等抽象要求必须由方言文件给出实际做法。

每条规则包含：

- `id`：稳定 ID，发布后不得复用；
- `source`：附件原始条款编号；
- `level`：`prohibition | mandatory | recommendation | reference`；
- `gate`：`block | warn | info`；
- `scope`：适用对象；
- `dialects`：规则适用的数据库方言；
- `condition`：可验证的判定条件；
- `check`：`static | manual | hybrid` 及检测提示；
- `examples`：正反例；
- `remediation`：整改建议；
- `confirmation_required`：是否必须进入开发者确认流程。

## 维护规则

1. 规则变更通过 PR，不直接改消费方 submodule 内文件。
2. 新增规则使用新 ID；语义变化不得静默覆盖旧规则。
3. 运行 `python3 scripts/validate_rules.py` 验证目录结构、154 条原文覆盖、方言路由、字段、枚举和 ID 唯一性。
4. 更新 `CHANGELOG.md`，按 `MAJOR.MINOR.PATCH` 判断版本：
   - MAJOR：删除规则、改变既有规则语义或新增会让既有合规代码失败的 Block；
   - MINOR：向后兼容地新增规则、检测器或模板能力；
   - PATCH：澄清、误报修复、示例或文档修订，不改变门禁语义。
5. 合并后创建签名 tag（如 `v1.1.0`）和 GitHub Release。

`source` 仅用于追溯，不代表公共仓库可以转载受限原文。发布前应由规范所有者确认授权和脱敏范围。

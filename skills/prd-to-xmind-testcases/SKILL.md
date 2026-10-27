---
name: prd-to-xmind-testcases
description: This skill should be used when a PRD, 需求文档, 产品方案 or 功能清单 needs to become a test case mind map that opens directly in XMind. It reads .pdf/.docx/.md/.txt requirement documents, splits every functional module, designs test points with positive, negative, boundary, equivalence, scenario and state-transition strategies, then generates a native .xmind file (plus .opml fallback and .md source). Trigger on "生成测试用例", "测试用例思维导图", "PRD 转 XMind", "根据需求文档写用例", "把需求拆成测试点", or when a user drops a PRD and asks what to test.
agent_created: true
---

# PRD → XMind 测试用例

把需求文档变成一份能**双击打开**的 XMind 测试用例脑图，而不是一段还需要手动导入的文本。

## 核心原则

1. **交付原生文件**。`.xmind` 是 zip 包（`content.json` + `metadata.json` + `manifest.json` + 缩略图），可直接生成，用户双击即开。不要只给 `.md` 让用户走「文件→导入→Markdown」。
2. **层级只有一个真相**。见 `references/testcase-structure.md`，五层：`#` 根 → `##` 模块 → `###` 子功能 → `####` 用例 → `-` 前置/步骤/预期。
3. **覆盖靠清单，不靠灵感**。见 `references/testcase-design-standard.md`，六个策略逐条过。
4. **歧义要登记**。PRD 的矛盾收敛到 `## 待确认问题`，见 `references/prd-review-checklist.md`。

## 工作流

### 1. 拿到文档

优先读技能目录下的 `requirements/`，其次是用户给的路径，也接受直接粘贴的正文。

```bash
python scripts/read_prd.py requirements/需求.pdf -o /tmp/prd.txt
python scripts/read_prd.py requirements/需求.docx --outline   # 只看章节骨架
```

支持 `.pdf`（PyMuPDF，缺失时回退 pypdf）、`.docx`（仅标准库）、`.txt`、`.md`。

文档超过 30 页时，先跑 `--outline` 看清章节结构，再决定模块怎么切，不要一上来逐页读。

### 2. 拆模块

按 PRD 章节切 `##`，一章一个模块，命名与文档用语一致。同时抽出：

- 全部业务规则编号（BR-xxx、规则表），这是后面验收覆盖率的对账依据；
- 全部状态机与枚举；
- 全部字段表（尤其必填、枚举、长度、联动）；
- 第 4 章的非功能性需求（性能指标、数据质量要求）——**这一章最容易被漏**。

### 3. 判路由

| 文档特征 | 加载 |
|----------|------|
| 默认 | `references/testcase-design-standard.md` |
| 出现接口路径/方法/错误码，或用户要求接口测试 | 追加 `references/api-testcases-standard.md` |
| 出现 SLA/RT/QPS/并发/超时/导出上限，或用户要求性能测试 | 追加 `references/performance-testcases-standard.md` |

路由看**文档内容**，不看用户有没有说「性能测试」。需求文档第 4 章自带指标时，必须加载性能规范。

### 4. 写大纲

输出 Markdown 到 `./output/<项目名>-测试用例.md`，严格按 `references/testcase-structure.md`：

- 标题格式 `类型-场景描述 [P0]`，类型是 `正向/反向/边界/场景/状态` 之一；
- **优先级必填**，`[P0]`/`[P1]`/`[P2]` 三选一，逐条判定，禁止整批默认 P1，判定口径见 `testcase-design-standard.md` 第二节；
- 每条用例至少 `- 步骤：` 和 `- 预期：`，需要特定数据时补 `- 前置：`；
- 预期必须可判定，禁止「显示正常」「功能可用」；
- 跨模块链路单独放 `## 端到端业务场景`；
- PRD 矛盾放 `## 待确认问题`。

写完后自查 P0 占比：正常落在 **20%~35%**。低于 10% 说明核心链路没识别出来，高于 45% 说明判定过宽。

### 5. 一条命令出产物

```bash
python scripts/build_all.py output/xxx-测试用例.md --expect-br 001-011,201-205
```

依次完成：格式校验 → 生成 `.xmind` → 生成 `.opml`。**校验不通过会中止，不产出任何文件**，避免把不合格的半成品交出去。

校验项：层级、`#` 空格、`-` 挂载位置、有序列表、缺步骤/预期、未标优先级、BOM；并输出模块/用例分布、类型分布、优先级分布（含各模块 P0 数）、BR 覆盖率。

需要单独跑时：

```bash
python scripts/validate_outline.py output/xxx.md --expect-br 001-011   # 只校验
python scripts/outline_to_xmind.py output/xxx.md --opml                # 只生成
```

产物三个文件：

| 文件 | 用途 |
|------|------|
| `.xmind` | 主交付，双击打开，XMind 2020+ |
| `.opml` | 兜底，XMind 8 等老版本用「文件→导入→OPML」 |
| `.md` | 源码，留给版本管理和二次生成 |

`[P0]/[P1]/[P2]` 会自动转成 XMind 红/黄/绿优先级图标，并从标题里去掉方括号，避免重复显示。

### 6. 交付说明

告诉用户：文件在哪、多少条用例、P0/P1/P2 各多少、覆盖了哪些模块、有几条待确认问题。不要复述文件内容。

## 目录约定

```
<技能目录>/
├── SKILL.md
├── requirements/     # 输入：把 PRD 丢这里
├── references/       # 规范，按需加载
└── scripts/
    ├── read_prd.py           # 抽 PDF/DOCX 文本与章节骨架
    ├── validate_outline.py   # 格式校验 + 覆盖度统计（含优先级闸门）
    ├── outline_to_xmind.py   # Markdown → .xmind / .opml
    └── build_all.py          # 校验 + 生成，一条命令跑完
```

输出默认写到**当前工作目录**的 `output/`，不要写回 `requirements/`，否则下次「列出目录下文件让用户选」时会把生成物当成输入。

## 用户只需做一件事

把 PRD 丢进 `requirements/`（或直接上传 PDF/Word），说一句「生成测试用例」。剩下的读文档、拆模块、判优先级、过闸门、出 `.xmind` 全自动完成。

## 禁止事项

- 只交付 `.md` 让用户手动导入；
- 用例不标优先级，或整批默认 P1；
- 用 `1.` `2.` 有序列表表达层级；
- 把 `-` 条目挂在 `##` 或 `###` 下；
- 层级跳级（`##` 直接接 `####`）；
- 文档没给数字却编造性能指标；
- 把 PRD 歧义自己拍板消化掉、不告知用户。

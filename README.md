# prd-to-xmind

**Turn a PRD into a test-case mind map you can actually open.**

A skill that reads a requirement document (PDF / DOCX / MD / TXT), designs test cases with six
strategies, and writes a **native `.xmind` file** — not a markdown outline you still have to import.

把一份需求文档丢进来，拿回一份双击就能打开的 XMind 测试用例脑图；顺带把文档里没说清的地方，
单独列成「待确认问题」一支。

- Live demo: <https://liyunchen.github.io/prd-to-testcases/>
- Source: <https://github.com/liyunchen/prd-to-testcases>
- Author: 李运辰 ·
- License: MIT

---

## What it actually produces

From a 46-page PRD (desensitised demo in [`demo/`](demo/)):

| | |
|---|---|
| 219 | test cases |
| 11 | L1 branches (10 functional modules + 1 open-questions branch) |
| 35 | sub-functions |
| 37 | business rules covered, 37/37 |
| 70 / 125 / 24 | P0 / P1 / P2 — P0 ratio 32% |

Three files come out of one command:

```
out.xmind   native file, double-click to open in XMind 2020+
out.opml    fallback for XMind 8 (File → Import → OPML)
out.md      source of truth, for version control and re-generation
```

## Why not just write markdown

- **Hierarchy has one truth.** `#` root → `##` module → `###` sub-function → `####` case →
  `- 前置/步骤/预期`. Bullets hung under a module become siblings of the case in XMind — the
  validator refuses that.
- **Priority is judged per case.** Every case carries `[P0]` / `[P1]` / `[P2]`, converted into
  XMind's red / amber / green markers. A batch of default P1 is treated as a defect.
- **Coverage is a checklist, not inspiration.** Six strategies per sub-function: positive,
  negative, boundary, equivalence, scenario, state transition.
- **Ambiguity is surfaced, not swallowed.** Contradictions in the PRD become a dedicated branch
  with location, conflict and affected cases — instead of being silently resolved.

## How it works

| Step | Script | What happens |
|---|---|---|
| Read | `read_prd.py` | PDF via PyMuPDF (pypdf fallback), DOCX via stdlib. `--outline` prints the chapter skeleton first for long docs |
| Split | — | One module per chapter; harvest every BR id, state machine, field table and the non-functional chapter |
| Route | — | SLA / RT / export limits → performance standard; API paths / error codes → API standard |
| Draft | — | Six strategies, per-case priority, scenario chains in a dedicated branch |
| Gate | `validate_outline.py` | Hierarchy, spacing, bullet placement, ordered lists, missing steps/expectations/priority, BR coverage |
| Emit | `outline_to_xmind.py` / `build_all.py` | `.xmind` + `.opml` + `.md` |

## Install

Three ways, same result — the skill directory lands in your `skills/` folder.

**1. Clone the repo**

```bash
git clone https://github.com/liyunchen/prd-to-testcases.git
cp -r prd-to-testcases/skills/prd-to-xmind-testcases ~/.workbuddy-ai/skills/
```

**2. Skill package**

```bash
unzip prd-to-xmind-testcases-1.0.0.zip -d ~/.workbuddy-ai/skills/
```

**3. Scripts only** — usable as a plain CLI, no skill installation needed

```bash
pip install pymupdf
python skills/prd-to-xmind-testcases/scripts/read_prd.py prd.pdf -o prd.txt
python skills/prd-to-xmind-testcases/scripts/build_all.py out.md \
    --expect-br 001-011,201-205
```

Requirements: Python 3.9+. `pymupdf` is optional (pypdf fallback); DOCX uses the standard library only.

## Usage

Put the PRD into `requirements/` (or pass a path) and say "生成测试用例". The rest is automatic:

```bash
python scripts/read_prd.py requirements/prd.pdf --outline   # 1. look at the skeleton
python scripts/read_prd.py requirements/prd.pdf -o /tmp/prd.txt
# 2. write output/<project>-测试用例.md following references/testcase-structure.md
python scripts/build_all.py output/<project>-测试用例.md --expect-br 001-011,601-610
```

## Repository layout

```
skills/prd-to-xmind-testcases/
├── SKILL.md                     # the workflow the agent follows
├── references/
│   ├── testcase-structure.md    # the only definition of the 5 layers
│   ├── testcase-design-standard.md
│   ├── api-testcases-standard.md
│   ├── performance-testcases-standard.md
│   └── prd-review-checklist.md  # six kinds of PRD ambiguity
└── scripts/
    ├── read_prd.py              # PDF / DOCX / TXT / MD → text + outline
    ├── validate_outline.py      # format gate + coverage stats
    ├── outline_to_xmind.py      # markdown → .xmind / .opml
    └── build_all.py             # validate + generate in one command

demo/
├── prd/                         # desensitised PRD (excerpt + full text)
├── output/                      # 219 cases: .md / .xmind / .opml
└── assets/                      # mind maps rendered from content.json

docs/                            # the landing page (GitHub Pages)
scripts/                         # repo tooling: desensitise, render, build data
dist/                            # installable skill package
```

## Demo data

The demo is a **desensitised** real PRD: customer names abstracted to industry descriptions,
internal system names replaced with generic ones, people replaced by roles, prototype links
removed. Business-line codes (`MTC / PAC / VASC-DMC / VASC-CMC / VASC-ECP / MAAS`) and all
business rules are kept as-is. The original 46-page PRD is not distributed.

`scripts/desensitize.py` applies one mapping table to both the PRD text and the case outline, then
runs a leak check against a forbidden-token list before anything is written.

## Regenerate the demo

脱敏脚本的输入是两份未入库的原始文件（含真实客户信息，不随仓库分发）：
`demo/prd/_raw.txt`（`read_prd.py` 抽取的原文）与 `demo/output/_raw.md`（含真实标识的用例大纲）。

```bash
python scripts/desensitize.py                       # PRD + outline, with leak self-check
python skills/prd-to-xmind-testcases/scripts/build_all.py \
    demo/output/客户中心一期-测试用例.md --expect-br 001-011,201-205,301-305,401-406,601-610
python scripts/render_mindmap.py demo/output/客户中心一期-测试用例.xmind \
    -o demo/assets/mindmap-overview.svg --depth 2 --counts
python scripts/build_demo_data.py                   # docs/data.js
```

## License

MIT © 李运辰 · 

#!/usr/bin/env python3
"""校验 Markdown 测试用例大纲是否符合 XMind 导入规范，并输出覆盖度统计。

用法:
    python validate_outline.py outline.md
    python validate_outline.py outline.md --expect-br 001-011,201-205

退出码 0 表示通过，1 表示存在格式错误。
"""

import argparse
import os
import re
import sys

TYPES = ('正向', '反向', '边界', '场景', '状态')


def expand_br(spec):
    """把 001-011,201-205 展开成 ['BR-001', ...]。"""
    out = []
    for part in spec.split(','):
        part = part.strip()
        if '-' in part:
            a, b = part.split('-')
            out += [f'BR-{i:03d}' for i in range(int(a), int(b) + 1)]
        elif part:
            out.append(f'BR-{int(part):03d}')
    return out


def main():
    ap = argparse.ArgumentParser(description='校验测试用例大纲格式')
    ap.add_argument('input')
    ap.add_argument('--expect-br', help='期望覆盖的业务规则编号，如 001-011,201-205')
    ap.add_argument('--allow-missing-priority', action='store_true',
                    help='允许用例不标优先级（默认缺优先级即视为不通过）')
    args = ap.parse_args()

    if not os.path.exists(args.input):
        sys.exit(f'找不到文件：{args.input}')

    raw = open(args.input, 'rb').read()
    warnings = []
    if raw[:3] == b'\xef\xbb\xbf':
        warnings.append('文件带 UTF-8 BOM，XMind 可能把首行标题识别为乱码，建议去掉')

    text = raw.decode('utf-8')
    lines = text.split('\n')

    errors = []
    counts = {1: 0, 2: 0, 3: 0, 4: 0}
    cur_level = 0
    bullets = 0
    last_case = None
    cases_without_steps = []
    cases_without_expect = []
    ordered = []
    modules = []
    cur_module = None
    types = {}
    priorities = {'P0': 0, 'P1': 0, 'P2': 0, '未标': 0}
    bullet_kinds = {}

    for lineno, line in enumerate(lines, 1):
        if not line.strip():
            continue

        if re.match(r'^- ', line):
            if cur_level != 4:
                errors.append(f'第 {lineno} 行：列表项不在 #### 测试点之下')
            bullets += 1
            m = re.match(r'^- (前置|步骤|预期|备注)[：:]', line)
            kind = m.group(1) if m else '其他'
            bullet_kinds[kind] = bullet_kinds.get(kind, 0) + 1
            if m and last_case is not None:
                last_case['kinds'].add(kind)
            continue

        if re.match(r'^\s*\d+[.、)]\s', line):
            ordered.append(lineno)
            continue

        if not line.startswith('#'):
            continue

        m = re.match(r'^(#{1,6})\s', line)
        if not m:
            errors.append(f'第 {lineno} 行：# 与标题之间缺少空格')
            continue

        level = len(m.group(1))
        if level > 4:
            errors.append(f'第 {lineno} 行：超过四级标题，XMind 层级会过深')
        if cur_level and level > cur_level + 1:
            errors.append(f'第 {lineno} 行：层级从 {cur_level} 跳到 {level}')

        if last_case and level > 4:
            if '步骤' not in last_case['kinds']:
                cases_without_steps.append(last_case['line'])
            if '预期' not in last_case['kinds']:
                cases_without_expect.append(last_case['line'])

        cur_level = level
        if level in counts:
            counts[level] += 1

        title = re.sub(r'^#+\s*', '', line).strip()

        if level == 2:
            cur_module = {'name': title, 'subs': 0, 'cases': 0, 'p0': 0}
            modules.append(cur_module)

        if level == 3 and cur_module is not None:
            cur_module['subs'] += 1

        if level == 4:
            if cur_module is not None:
                cur_module['cases'] += 1
            last_case = {'line': lineno, 'kinds': set()}
            tm = re.match(rf'^({"|".join(TYPES)})-', title)
            key = tm.group(1) if tm else '其他'
            types[key] = types.get(key, 0) + 1
            pm = re.search(r'\[(P[0-2])\]', title)
            priorities[pm.group(1) if pm else '未标'] += 1
            if pm and pm.group(1) == 'P0' and cur_module is not None:
                cur_module['p0'] += 1

    if last_case:
        if '步骤' not in last_case['kinds']:
            cases_without_steps.append(last_case['line'])
        if '预期' not in last_case['kinds']:
            cases_without_expect.append(last_case['line'])

    if counts[1] == 0:
        errors.append('缺少一级标题（# 根主题）')
    elif counts[1] > 1:
        errors.append(f'存在 {counts[1]} 个一级标题，XMind 只认第一个作为中心主题')
    if ordered:
        errors.append(f'{len(ordered)} 行使用了有序列表，XMind 无法映射：第 {ordered[:5]} 行')
    if cases_without_steps:
        errors.append(f'{len(cases_without_steps)} 条用例缺「步骤」：第 {cases_without_steps[:5]} 行')
    if cases_without_expect:
        errors.append(f'{len(cases_without_expect)} 条用例缺「预期」：第 {cases_without_expect[:5]} 行')

    total_cases = counts[4]
    p0_ratio = (100 * priorities['P0'] / total_cases) if total_cases else 0

    if priorities['未标'] and not args.allow_missing_priority:
        errors.append(f'{priorities["未标"]} 条用例未标优先级，请在标题末尾补 [P0]/[P1]/[P2]'
                      f'（确需跳过时加 --allow-missing-priority）')
    if total_cases and (p0_ratio < 10 or p0_ratio > 45):
        warnings.append(f'P0 占比 {p0_ratio:.1f}% 偏离合理区间 20%~35%：'
                        f'低于 10% 可能漏了核心链路，高于 45% 说明判定过宽')

    print(f'根主题 {counts[1]} / 模块 {counts[2]} / 子功能 {counts[3]} / 用例 {counts[4]}')
    print(f'条目 {bullets} 条，明细 {bullet_kinds}')
    print(f'类型分布 {types}')
    total = total_cases
    p0 = priorities['P0']
    ratio = p0_ratio
    print(f'优先级 {priorities}（P0 占比 {ratio:.1f}%）')

    if modules:
        print(f'\n{"模块":<24}{"子功能":>6}{"用例":>6}{"P0":>6}')
        for m in modules:
            print(f'{m["name"][:22]:<24}{m["subs"]:>8}{m["cases"]:>8}{m["p0"]:>6}')

    brs = set(re.findall(r'BR-(\d{3})', text))
    if brs:
        print(f'\n业务规则引用 {len(brs)} 条：{", ".join("BR-" + b for b in sorted(brs))}')

    if args.expect_br:
        expect = expand_br(args.expect_br)
        missing = [b for b in expect if b[3:] not in brs]
        if missing:
            errors.append(f'未覆盖的业务规则：{", ".join(missing)}')
        else:
            print(f'业务规则覆盖 {len(expect)}/{len(expect)} ✅')

    for w in warnings:
        print(f'\n⚠️  {w}')

    if errors:
        print('\n❌ 校验未通过：')
        for e in errors:
            print('  -', e)
        sys.exit(1)

    print('\n✅ 格式校验通过，可直接生成 .xmind')


if __name__ == '__main__':
    main()

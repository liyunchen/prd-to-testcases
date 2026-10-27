#!/usr/bin/env python3
"""把测试用例大纲解析成页面用的 JSON（docs/data.js）。

只导出页面要展开的模块，其余只给统计数字，避免整份 219 条塞进首屏。
"""

import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'demo', 'output', '客户中心一期-测试用例.md')
OUT = os.path.join(ROOT, 'docs', 'data.js')

TYPES = ('正向', '反向', '边界', '场景', '状态')
EXPAND = ('2.1 创建客户', '2.6 客户合并')


def parse(path):
    modules = []
    cur_m = cur_s = cur_c = None
    for raw in io.open(path, encoding='utf-8'):
        line = raw.rstrip('\n')
        if not line.strip():
            continue
        if line.startswith('#### '):
            title = line[5:].strip()
            m = re.search(r'\[(P[0-2])\]', title)
            tm = re.match(rf'^({"|".join(TYPES)})-', title)
            cur_c = {
                'title': re.sub(r'\s*\[P[0-2]\]$', '', title).strip(),
                'type': tm.group(1) if tm else '',
                'priority': m.group(1) if m else '',
                'pre': '', 'steps': '', 'expect': '', 'note': '',
            }
            if cur_s is not None:
                cur_s['cases'].append(cur_c)
        elif line.startswith('### '):
            cur_s = {'title': line[4:].strip(), 'cases': []}
            if cur_m is not None:
                cur_m['subs'].append(cur_s)
            cur_c = None
        elif line.startswith('## '):
            cur_m = {'title': line[3:].strip(), 'subs': []}
            modules.append(cur_m)
            cur_s = None
            cur_c = None
        elif line.startswith('- ') and cur_c is not None:
            key, _, val = line[2:].partition('：')
            key = key.strip()
            mapping = {'前置': 'pre', '步骤': 'steps', '预期': 'expect', '备注': 'note'}
            if key in mapping:
                cur_c[mapping[key]] = val.strip()
    return modules


def main():
    if not os.path.exists(SRC):
        sys.exit(f'缺少源文件：{SRC}')
    modules = parse(SRC)

    total_cases = sum(len(s['cases']) for m in modules for s in m['subs'])
    prio = {'P0': 0, 'P1': 0, 'P2': 0}
    types = {t: 0 for t in TYPES}
    for m in modules:
        for s in m['subs']:
            for c in s['cases']:
                if c['priority'] in prio:
                    prio[c['priority']] += 1
                if c['type'] in types:
                    types[c['type']] += 1

    text = io.open(SRC, encoding='utf-8').read()
    brs = sorted(set(re.findall(r'BR-(\d{3})', text)))

    questions = [m['title'] for m in modules if '待确认' in m['title']
                 for m in [m] for _ in [0]]
    q_items = []
    for m in modules:
        if '待确认' in m['title']:
            q_items = [s['title'] for s in m['subs']]

    payload = {
        'stats': {
            'cases': total_cases,
            'modules': len([m for m in modules if '待确认' not in m['title']]),
            'subs': sum(len(m['subs']) for m in modules if '待确认' not in m['title']),
            'brs': len(brs),
            'branches': len(modules),
            'priority': prio,
            'types': types,
        },
        'moduleIndex': [
            {'title': m['title'],
             'cases': sum(len(s['cases']) for s in m['subs']),
             'subs': len(m['subs'])}
            for m in modules if '待确认' not in m['title']
        ],
        'modules': [m for m in modules if m['title'] in EXPAND],
        'questions': q_items,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('// 由 scripts/build_demo_data.py 生成，请勿手改\n')
        f.write('window.DEMO_DATA = ')
        f.write(json.dumps(payload, ensure_ascii=False, indent=1))
        f.write(';\n')

    print(f'✅ {os.path.relpath(OUT, ROOT)}')
    print(f'   用例 {total_cases} / 模块 {payload["stats"]["modules"]} / 子功能 {payload["stats"]["subs"]}')
    print(f'   优先级 {prio} / 类型 {types} / BR {len(brs)} / 待确认 {len(q_items)}')
    print(f'   展开模块：{", ".join(m["title"] for m in payload["modules"])}')


if __name__ == '__main__':
    main()

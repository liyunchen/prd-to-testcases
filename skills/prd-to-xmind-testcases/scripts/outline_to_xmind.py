#!/usr/bin/env python3
"""把 Markdown 测试用例大纲转换成 XMind 原生文件（.xmind）与 OPML。

用法:
    python outline_to_xmind.py outline.md
    python outline_to_xmind.py outline.md -o 测试用例.xmind --opml

Markdown 层级约定（与 references/testcase-structure.md 一致）:
    #    根主题
    ##   功能模块
    ###  子功能
    #### 测试用例（标题可带 [P0]/[P1]/[P2] 优先级标记）
    -    前置 / 步骤 / 预期

生成的 .xmind 是一个 zip 包，内含 content.json + metadata.json + manifest.json
+ Thumbnails/thumbnail.png，双击即可用 XMind 2020 及以上版本打开。
OPML 供 XMind 8 等老版本导入兜底。
"""

import argparse
import json
import os
import re
import sys
import uuid
import zipfile
from xml.sax.saxutils import escape

PRIORITY_RE = re.compile(r'\[(P[0-2])\]')
PRIORITY_MARKER = {'P0': 'priority-1', 'P1': 'priority-2', 'P2': 'priority-3'}
BULLET_KINDS = ('前置', '步骤', '预期', '备注')


def uid():
    return uuid.uuid4().hex


def parse_markdown(path):
    """把 Markdown 大纲解析成嵌套节点树。返回 (root, errors)。"""
    root = None
    stack = {}
    last_case = None
    errors = []
    depth_seen = 0

    with open(path, encoding='utf-8-sig') as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.rstrip('\n')
            if not line.strip():
                continue

            level, text = None, None
            if line.startswith('# '):
                level, text = 1, line[2:]
            elif line.startswith('## '):
                level, text = 2, line[3:]
            elif line.startswith('### '):
                level, text = 3, line[4:]
            elif line.startswith('#### '):
                level, text = 4, line[5:]
            elif re.match(r'^- ', line):
                level, text = 5, line[2:]
            elif re.match(r'^\s*\d+[.、)]\s', line):
                errors.append(f'第 {lineno} 行：使用了有序列表，XMind 无法映射为节点，请改用 "- "')
                continue
            elif line.startswith('#'):
                errors.append(f'第 {lineno} 行：# 与标题之间缺少空格')
                continue
            else:
                continue

            if level == 1:
                root = {'title': text.strip(), 'children': [], 'priority': None}
                stack = {1: root}
                depth_seen = 1
                continue

            if root is None:
                errors.append(f'第 {lineno} 行：缺少一级标题（# 根主题）')
                continue

            if level > depth_seen + 1:
                errors.append(f'第 {lineno} 行：层级从 {depth_seen} 跳到 {level}，缺少父级')
            depth_seen = level

            if level == 5:
                if last_case is None:
                    errors.append(f'第 {lineno} 行：列表项不在 #### 测试点之下')
                    continue
                last_case['children'].append(
                    {'title': text.strip(), 'children': [], 'priority': None})
                continue

            parent = stack.get(level - 1)
            if parent is None:
                errors.append(f'第 {lineno} 行：找不到上一级节点')
                continue

            m = PRIORITY_RE.search(text)
            node = {
                'title': PRIORITY_RE.sub('', text).strip(),
                'children': [],
                'priority': m.group(1) if m else None,
            }
            parent['children'].append(node)
            stack[level] = node
            for k in list(stack):
                if k > level:
                    del stack[k]
            last_case = node if level == 4 else None

    if root is None:
        errors.append('未找到一级标题，文件不是有效的大纲')
    return root, errors


def to_xmind_topic(node, is_root=False):
    topic = {'id': uid(), 'class': 'topic', 'title': node['title']}
    if node.get('priority'):
        topic['markers'] = [{'markerId': PRIORITY_MARKER[node['priority']]}]
    if node['children']:
        topic['children'] = {'attached': [to_xmind_topic(c) for c in node['children']]}
    if is_root:
        topic['structureClass'] = 'org.xmind.ui.logic.right'
    return topic


def count_nodes(node):
    return 1 + sum(count_nodes(c) for c in node['children'])


def build_thumbnail(path, root_title, case_count):
    """生成 XMind 首页缩略图，失败则跳过（不影响打开）。"""
    try:
        import fitz
    except ImportError:
        return False
    try:
        doc = fitz.open()
        page = doc.new_page(width=480, height=300)
        page.draw_rect(fitz.Rect(0, 0, 480, 300), color=None, fill=(0.98, 0.98, 0.99))
        page.insert_text((36, 140), root_title[:22], fontsize=20,
                         fontname='china-s', color=(0.05, 0.27, 0.49))
        page.insert_text((36, 178), f'测试用例 · {case_count} 条', fontsize=13,
                         fontname='china-s', color=(0.35, 0.35, 0.4))
        page.get_pixmap().save(path)
        return True
    except Exception:
        return False


def write_xmind(root, out_path, thumb_path=None):
    sheet_id = uid()
    content = [{
        'id': sheet_id,
        'class': 'sheet',
        'title': root['title'],
        'rootTopic': to_xmind_topic(root, is_root=True),
    }]
    metadata = {
        'creator': {'name': 'XMind', 'version': '12.0.0'},
        'activeSheetId': sheet_id,
        'dataStructureVersion': '2',
    }
    entries = {'content.json': {}, 'metadata.json': {}}
    if thumb_path:
        entries['Thumbnails/thumbnail.png'] = {}
    manifest = {'file-entries': entries}

    with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('content.json', json.dumps(content, ensure_ascii=False))
        z.writestr('metadata.json', json.dumps(metadata, ensure_ascii=False))
        z.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False))
        if thumb_path:
            z.write(thumb_path, 'Thumbnails/thumbnail.png')


def write_opml(root, out_path):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<opml version="2.0">',
             '  <head>', f'    <title>{escape(root["title"])}</title>', '  </head>',
             '  <body>']

    def walk(node, depth):
        pad = '  ' * depth
        lines.append(f'{pad}<outline text="{escape(node["title"])}">')
        for child in node['children']:
            walk(child, depth + 1)
        lines.append(f'{pad}</outline>')

    walk(root, 2)
    lines += ['  </body>', '</opml>']
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def main():
    ap = argparse.ArgumentParser(description='Markdown 大纲 → XMind 原生文件')
    ap.add_argument('input', help='Markdown 大纲文件')
    ap.add_argument('-o', '--output', help='输出 .xmind 路径，默认与输入同名')
    ap.add_argument('--opml', action='store_true', help='同时生成 .opml 兜底文件')
    args = ap.parse_args()

    if not os.path.exists(args.input):
        sys.exit(f'找不到文件：{args.input}')

    root, errors = parse_markdown(args.input)
    if errors:
        print('大纲格式存在问题：', file=sys.stderr)
        for e in errors[:20]:
            print('  -', e, file=sys.stderr)
        sys.exit(1)

    out = args.output or os.path.splitext(args.input)[0] + '.xmind'
    os.makedirs(os.path.dirname(os.path.abspath(out)) or '.', exist_ok=True)

    cases = []

    def collect(node, depth):
        if depth == 4:
            cases.append(node)
        for c in node['children']:
            collect(c, depth + 1)

    collect(root, 1)

    thumb = os.path.join(os.path.dirname(os.path.abspath(out)), '_thumb_tmp.png')
    has_thumb = build_thumbnail(thumb, root['title'], len(cases))
    try:
        write_xmind(root, out, thumb if has_thumb else None)
    finally:
        if has_thumb and os.path.exists(thumb):
            os.remove(thumb)

    total = count_nodes(root)
    size_kb = os.path.getsize(out) / 1024
    print(f'✅ 已生成 {out}')
    print(f'   节点 {total} 个 / 用例 {len(cases)} 条 / {size_kb:.1f} KB')
    print(f'   L1 分支：{" / ".join(c["title"] for c in root["children"])}')

    if args.opml:
        op = os.path.splitext(out)[0] + '.opml'
        write_opml(root, op)
        print(f'✅ 已生成兜底文件 {op}（XMind 8 用 文件→导入→OPML）')


if __name__ == '__main__':
    main()

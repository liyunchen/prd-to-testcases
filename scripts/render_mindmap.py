#!/usr/bin/env python3
"""把 .xmind 的 content.json 渲染成 SVG 脑图预览，供网页与 README 使用。

不需要安装 XMind，也不依赖浏览器。

用法:
    python scripts/render_mindmap.py a.xmind -o overview.svg --depth 2
    python scripts/render_mindmap.py a.xmind -o detail.svg --branch "2.1 创建客户" --depth 3
"""

import argparse
import json
import math
import os
import sys
import zipfile
from xml.sax.saxutils import escape

FONT_STACK = ("Inter, 'Helvetica Neue', Arial, 'PingFang SC', "
              "'Hiragino Sans GB', 'Microsoft YaHei', sans-serif")

PRIORITY_COLOR = {'priority-1': '#B23A2E', 'priority-2': '#C98A1B', 'priority-3': '#3F7A4E'}

# 每层字号、内边距、行高
STYLE = {
    0: dict(size=17, padx=20, pady=13, weight=600, fill='#14110F', text='#FBFAF7'),
    1: dict(size=13, padx=14, pady=9, weight=600, fill='#F7F3EA', text='#14110F'),
    2: dict(size=11.5, padx=12, pady=7, weight=500, fill='#FFFFFF', text='#2B2621'),
    3: dict(size=10.5, padx=11, pady=6, weight=400, fill='#FFFFFF', text='#3A342D'),
}
GAP_X = {0: 46, 1: 34, 2: 26}
GAP_Y = {1: 10, 2: 5, 3: 3}


def text_width(s, size):
    w = 0.0
    for ch in s:
        if ord(ch) > 0x2E80:
            w += size * 1.02
        elif ch in 'iljI.,:;|!\'`':
            w += size * 0.30
        elif ch.isupper():
            w += size * 0.62
        else:
            w += size * 0.54
    return w


def load_root(path, branch=None):
    with zipfile.ZipFile(path) as z:
        content = json.loads(z.read('content.json').decode('utf-8'))
    root = content[0]['rootTopic']

    def norm(n):
        return {
            'title': n.get('title', ''),
            'markers': n.get('markers', []),
            'children': [norm(c) for c in n.get('children', {}).get('attached', [])],
        }

    root = norm(root)
    if branch:
        for child in root['children']:
            if child['title'].startswith(branch):
                return child
        sys.exit(f'找不到分支：{branch}')
    return root


def annotate(node):
    """统计每条分支下的用例数，写到标题后缀。"""
    def count(n):
        total = sum(count(c) for c in n['children'])
        return total + (1 if not n['children'] else 0)
    return count(node)


def trim(node, depth, cur=0):
    if cur >= depth - 1:
        node['children'] = []
    else:
        for c in node['children']:
            trim(c, depth, cur + 1)


def count_cases(node, rel=1):
    """统计模块下的用例数：优先数第三层节点，没有则数第二层。"""
    deep = []
    for sub in node['children']:
        deep.extend(sub['children'])
    return len(deep) if deep else len(node['children'])


def measure(node, depth):
    st = STYLE.get(depth, STYLE[3])
    node['_st'] = st
    extra = 8 if node.get('markers') else 0
    node['_w'] = text_width(node['title'], st['size']) + st['padx'] * 2 + extra
    node['_h'] = st['size'] + st['pady'] * 2          # 自身盒子高度
    node['_span'] = node['_h']                        # 子树占用高度
    if node['children']:
        for c in node['children']:
            measure(c, depth + 1)
        total = sum(c['_span'] for c in node['children']) + GAP_Y.get(depth + 1, 3) * (len(node['children']) - 1)
        node['_span'] = max(node['_h'], total)
    return node


def place(node, depth, x, y_top, col_w):
    node['_x'] = x
    node['_y'] = y_top + node['_span'] / 2
    if not node['children']:
        return
    gap = GAP_Y.get(depth + 1, 3)
    total = sum(c['_span'] for c in node['children']) + gap * (len(node['children']) - 1)
    cy = node['_y'] - total / 2
    for c in node['children']:
        place(c, depth + 1, x + col_w[depth] + GAP_X.get(depth, 24), cy, col_w)
        cy += c['_span'] + gap


def collect_cols(node, depth, col_w):
    if depth >= len(col_w):
        col_w.append(0)
    col_w[depth] = max(col_w[depth], node['_w'])
    for c in node['children']:
        collect_cols(c, depth + 1, col_w)


def emit(node, depth, out):
    st = node['_st']
    x = node['_x']
    y = node['_y'] - node['_h'] / 2
    w, h = node['_w'], node['_h']
    radius = 7 if depth < 3 else 5
    stroke = '#DCD5C6' if depth > 0 else 'none'
    out.append(
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{radius}" '
        f'fill="{st["fill"]}" stroke="{stroke}" stroke-width="1"/>'
    )
    # 优先级圆点
    if node['markers']:
        mid = node['markers'][0].get('markerId')
        color = PRIORITY_COLOR.get(mid)
        if color:
            out.append(f'<circle cx="{x + 7:.1f}" cy="{node["_y"]:.1f}" r="2.8" fill="{color}"/>')
    tx = x + w / 2
    out.append(
        f'<text x="{tx:.1f}" y="{node["_y"] + st["size"] * 0.36:.1f}" '
        f'font-family="{FONT_STACK}" font-size="{st["size"]}" font-weight="{st["weight"]}" '
        f'fill="{st["text"]}" text-anchor="middle">{escape(node["title"])}</text>'
    )
    if not node['children']:
        return
    for c in node['children']:
        x1 = x + w
        y1 = node['_y']
        x2 = c['_x']
        y2 = c['_y']
        dx = max(14.0, (x2 - x1) * 0.45)
        out.append(
            f'<path d="M{x1:.1f},{y1:.1f} C{x1 + dx:.1f},{y1:.1f} {x2 - dx:.1f},{y2:.1f} {x2:.1f},{y2:.1f}" '
            f'fill="none" stroke="#D8D1C4" stroke-width="1.2"/>'
        )
        emit(c, depth + 1, out)


def render(path, out_path, depth, branch=None, caption=None, counts=False, head=None):
    root = load_root(path, branch)
    if head:
        root['children'] = root['children'][:head]
    if counts:
        for c in root['children']:
            n = count_cases(c)
            if n:
                c['title'] = f'{c["title"]}  ·  {n}'
    trim(root, depth)
    measure(root, 0)
    col_w = []
    collect_cols(root, 0, col_w)
    total_w = sum(col_w) + sum(GAP_X.get(i, 24) for i in range(len(col_w) - 1))
    place(root, 0, 0, 0, col_w)

    pad = 18
    body = []
    emit(root, 0, body)
    height = root['_span']
    width = total_w

    cap_h = 0
    if caption:
        cap_h = 30
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width + pad * 2:.0f} {height + pad * 2 + cap_h:.0f}" '
        f'width="{width + pad * 2:.0f}" height="{height + pad * 2 + cap_h:.0f}" role="img">',
        f'<g transform="translate({pad},{pad})">',
    ]
    svg += body
    svg.append('</g>')
    if caption:
        svg.append(
            f'<text x="{pad}" y="{height + pad * 2 + 8:.0f}" font-family="{FONT_STACK}" '
            f'font-size="10.5" fill="#8A8074">{escape(caption)}</text>'
        )
    svg.append('</svg>')

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(svg))
    print(f'✅ {out_path}  ({width:.0f}×{height + cap_h:.0f})')


def main():
    ap = argparse.ArgumentParser(description='.xmind → SVG 预览')
    ap.add_argument('input')
    ap.add_argument('-o', '--output', required=True)
    ap.add_argument('--depth', type=int, default=3, help='保留层数，0 为只画根节点')
    ap.add_argument('--branch', help='只渲染指定一级分支，如 "2.1 创建客户"')
    ap.add_argument('--caption', help='图下角注释')
    ap.add_argument('--counts', action='store_true', help='在一级分支后标注用例数')
    ap.add_argument('--head', type=int, help='只保留前 N 个子分支')
    args = ap.parse_args()
    render(args.input, args.output, args.depth, args.branch, args.caption, args.counts, args.head)


if __name__ == '__main__':
    main()

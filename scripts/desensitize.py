#!/usr/bin/env python3
"""把 PRD 文本与测试用例大纲做统一脱敏，保证页面展示与下载文件口径一致。

用法:
    python scripts/desensitize.py --check          # 只做泄露自检
    python scripts/desensitize.py                  # 生成脱敏产物

映射采用「行业泛称」策略：客户名与系统名抽象为行业描述，人名替换为角色，
业务线代号（MTC/PAC/VASC-*）按要求保留。
"""

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 顺序敏感：长串、专有组合必须排在通用词之前
RULES = [
    # 链接
    ('✏️原型图：https://e6639051-blip.github.io/crm/', '原型图：（内部原型链接已移除）'),
    ('https://e6639051-blip.github.io/crm/', '（内部原型链接已移除）'),
    # 客户编号字段
    ('source_customer_uec', 'source_customer_id'),
    ('target_customer_uec', 'target_customer_id'),
    ('客户编号 uec', '客户编号'),
    ('原客户 uec', '原客户编号'),
    ('uec', '客户编号'),
    # 系统名
    ('甄零系统合同流水号', '电子签系统合同流水号'),
    ('甄零系统', '电子签系统'),
    ('甄零', '电子签系统'),
    ('BOP广告主ID', '投放平台广告主ID'),
    ('BOP 广告主 ID', '投放平台广告主 ID'),
    ('BOP广告主', '投放平台广告主'),
    ('BOP', '投放平台'),
    ('BPMS', '业务中台'),
    ('CRM', '客户系统'),
    # 广告主缩写
    ('广告主（ADV）', '广告主'),
    ('广告主(ADV)', '广告主'),
    ('adv币种', '广告主币种'),
    ('ADV', '广告主'),
    # 内部 BU 代号
    ('Sparkfly', 'BU-A'),
    ('LiveLab', 'BU-D'),
    ('3MC', 'BU-E'),
    ('ITC', 'BU-F'),
    ('CFC', 'BU-B'),
    ('GFC', 'BU-C'),
    # 客户
    ('腾讯科技（深圳）有限公司', '某头部视频平台客户'),
    ('北京字节跳动科技有限公司', '某短视频平台客户'),
    ('广州网易计算机系统有限公司', '某门户网站客户A'),
    ('网易（杭州）网络有限公司', '某门户网站客户B'),
    ('腾讯', '某头部视频平台'),
    ('字节跳动', '某短视频平台'),
    ('网易', '某门户网站'),
    # 人名
    ('张朝佳', '产品经理'),
    ('陈璐', '业务负责人'),
    ('周涛', '技术负责人'),
    ('沈树帆', 'MTC审批人'),
    ('罗格', 'PAC审批人'),
    ('林焕滨', 'VASC审批人'),
    ('张三', '责任BD-1'),
    ('李四', '责任BD-2'),
    ('王五', '责任BD-3'),
    ('赵六', '责任BD-4'),
    ('陈七', '责任CM-1'),
    # 编号样例
    ('KH-202610000001', 'KH-202601000001'),
]

# 替换后不应再出现的词，用于自检
FORBIDDEN = [
    'BPMS', 'CRM', '甄零', 'BOP', 'ADV', 'uec',
    '腾讯', '字节跳动', '网易',
    '张朝佳', '陈璐', '周涛', '沈树帆', '罗格', '林焕滨',
    '张三', '李四', '王五', '赵六', '陈七',
    'Sparkfly', 'LiveLab', 'CFC', 'GFC', '3MC', 'ITC',
    'e6639051', 'github.io/crm',
]

# 标题特例：避免出现「客户中心一期（客户系统）」这种别扭写法
TITLE_RULE = ('# 客户中心一期（CRM）测试用例', '# 客户中心一期 测试用例（脱敏样例）')


def apply_rules(text):
    hits = {}
    if TITLE_RULE[0] in text:
        text = text.replace(*TITLE_RULE)
        hits[TITLE_RULE[0]] = hits.get(TITLE_RULE[0], 0) + 1
    for old, new in RULES:
        n = text.count(old)
        if n:
            text = text.replace(old, new)
            hits[old] = hits.get(old, 0) + n
    # 清理替换产生的重复措辞
    text = text.replace('广告主（广告主）', '广告主')
    text = text.replace('广告主广告主', '广告主')
    text = text.replace('客户编号 ', '客户编号')
    text = text.replace('业务中台业务中台', '业务中台')
    return text, hits


def check(text, name):
    leaked = [w for w in FORBIDDEN if w in text]
    if leaked:
        print(f'❌ {name} 仍含未脱敏词：{", ".join(leaked)}')
        return False
    print(f'✅ {name} 泄露自检通过')
    return True


def read(path):
    return io.open(path, encoding='utf-8').read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, 'w', encoding='utf-8', newline='\n').write(text)


def prd_to_md(raw):
    """把 read_prd.py 的纯文本输出整理成可读 Markdown。"""
    lines = []
    for line in raw.split('\n'):
        m = re.match(r'^===== PAGE (\d+) =====$', line.strip())
        if m:
            lines.append('')
            lines.append(f'<!-- p{m.group(1)} -->')
            lines.append('')
            continue
        lines.append(line)
    body = '\n'.join(lines)
    body = re.sub(r'\n{3,}', '\n\n', body).strip()
    header = (
        '# 客户中心一期 PRD（脱敏版）\n\n'
        '> 原始文档 46 页。本文件为客户中心一期需求文档的**脱敏全文**，用于演示'
        '「PRD → 测试用例脑图」链路。\n'
        '> 已处理：客户名称抽象为行业描述、内部系统名替换为通用叫法、人员姓名替换为角色、'
        '内部原型链接移除、客户编号样例改写。\n'
        '> 业务线代号（MTC / PAC / VASC-DMC / VASC-CMC / VASC-ECP / MAAS）与全部业务规则原文保留。\n\n'
        '---\n\n'
    )
    return header + body


def main():
    only_check = '--check' in sys.argv

    prd_src = os.path.join(ROOT, 'demo', 'prd', '_raw.txt')
    outline_src = os.path.join(ROOT, 'demo', 'output', '_raw.md')
    prd_out = os.path.join(ROOT, 'demo', 'prd', '客户中心-需求文档-脱敏版.md')
    outline_out = os.path.join(ROOT, 'demo', 'output', '客户中心一期-测试用例.md')

    if only_check:
        ok = True
        for p in (prd_out, outline_out):
            if os.path.exists(p):
                ok &= check(read(p), os.path.basename(p))
        sys.exit(0 if ok else 1)

    for p in (prd_src, outline_src):
        if not os.path.exists(p):
            sys.exit(f'缺少源文件：{p}')

    prd_text, h1 = apply_rules(prd_to_md(read(prd_src)))
    outline_text, h2 = apply_rules(read(outline_src))

    write(prd_out, prd_text)
    write(outline_out, outline_text)

    print(f'✅ 已生成 {os.path.relpath(prd_out, ROOT)}')
    print(f'✅ 已生成 {os.path.relpath(outline_out, ROOT)}')
    print(f'\nPRD 命中规则 {len(h1)} 条，用例命中规则 {len(h2)} 条')
    top = sorted(h2.items(), key=lambda kv: -kv[1])[:8]
    print('用例侧高频替换：' + '，'.join(f'{k}×{v}' for k, v in top))

    ok = check(prd_text, 'PRD 脱敏版') & check(outline_text, '用例脱敏版')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()

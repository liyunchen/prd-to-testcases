#!/usr/bin/env python3
"""一条命令完成：格式校验 → 生成 .xmind → 生成 .opml。

用法:
    python build_all.py output/xxx-测试用例.md
    python build_all.py output/xxx-测试用例.md --expect-br 001-011,201-205

校验不通过时立即中止，不生成任何文件，避免把不合格的产物交出去。
"""

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def run(script, args):
    cmd = [PY, os.path.join(HERE, script)] + args
    return subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')


def main():
    ap = argparse.ArgumentParser(description='校验并生成 XMind 测试用例产物')
    ap.add_argument('input', help='Markdown 大纲文件')
    ap.add_argument('-o', '--output', help='输出 .xmind 路径，默认与输入同名')
    ap.add_argument('--expect-br', help='期望覆盖的业务规则编号，如 001-011,201-205')
    ap.add_argument('--allow-missing-priority', action='store_true')
    args = ap.parse_args()

    v_args = [args.input]
    if args.expect_br:
        v_args += ['--expect-br', args.expect_br]
    if args.allow_missing_priority:
        v_args.append('--allow-missing-priority')

    print('① 校验大纲…')
    v = run('validate_outline.py', v_args)
    print(v.stdout.rstrip())
    if v.returncode != 0:
        print(v.stderr.rstrip(), file=sys.stderr)
        sys.exit('\n✋ 校验未通过，已中止生成。先修大纲，不要交付半成品。')

    print('\n② 生成 XMind…')
    g_args = [args.input, '--opml']
    if args.output:
        g_args += ['-o', args.output]
    g = run('outline_to_xmind.py', g_args)
    print(g.stdout.rstrip())
    if g.returncode != 0:
        print(g.stderr.rstrip(), file=sys.stderr)
        sys.exit('生成失败')

    print('\n✅ 全部完成。.xmind 双击打开；老版本 XMind 用 .opml 导入。')


if __name__ == '__main__':
    main()

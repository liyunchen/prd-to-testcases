#!/usr/bin/env python3
"""抽取 PRD / 需求文档的纯文本，便于逐节阅读与拆分模块。

支持 .pdf / .docx / .txt / .md，输出带页码或段落标记的 UTF-8 文本。

用法:
    python read_prd.py 需求.pdf                 # 打印到终端
    python read_prd.py 需求.pdf -o prd.txt      # 写入文件
    python read_prd.py 需求.docx --outline      # 只输出疑似标题行（章节骨架）

PDF 优先用 PyMuPDF(fitz)，缺失时回退 pypdf；DOCX 只用标准库，无需 python-docx。
"""

import argparse
import os
import re
import sys
import zipfile


def read_pdf(path):
    try:
        import fitz
    except ImportError:
        fitz = None

    if fitz is not None:
        doc = fitz.open(path)
        parts = []
        for i in range(doc.page_count):
            parts.append(f'===== PAGE {i + 1} =====')
            parts.append(doc[i].get_text())
        return '\n'.join(parts), doc.page_count

    try:
        from pypdf import PdfReader
    except ImportError:
        sys.exit('需要 PyMuPDF 或 pypdf 才能解析 PDF：pip install pymupdf')

    reader = PdfReader(path)
    parts = []
    for i, page in enumerate(reader.pages, 1):
        parts.append(f'===== PAGE {i} =====')
        parts.append(page.extract_text() or '')
    return '\n'.join(parts), len(reader.pages)


def read_docx(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read('word/document.xml').decode('utf-8', 'ignore')
    xml = re.sub(r'<w:tab[^>]*/>', '\t', xml)
    xml = re.sub(r'</w:p>', '\n', xml)
    xml = re.sub(r'<w:br[^>]*/>', '\n', xml)
    text = re.sub(r'<[^>]+>', '', xml)
    text = (text.replace('&amp;', '&').replace('&lt;', '<')
                .replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'"))
    lines = [ln.strip() for ln in text.split('\n')]
    return '\n'.join(ln for ln in lines if ln), len(lines)


def read_plain(path):
    text = open(path, encoding='utf-8', errors='ignore').read()
    return text, text.count('\n') + 1


def looks_like_heading(line):
    s = line.strip().replace('\u200b', '')
    if not s or len(s) > 40:
        return False

    m = re.match(r'^\d+(\.\d+)*[.、]?\s+(.*)$', s)
    body = m.group(2) if m else s
    if not body:
        return False
    # 步骤句特征：以动作为主、带箭头、带句末标点、带引号开头
    if body[-1] in '。！？:：?!"”':
        return False
    if '→' in body or '：' in body:
        return False
    if re.match(r'^(用户|系统|点击|若|如果|当|在|选择|输入|返回|进入|打开|关闭|提交|表单|不|"|“)', body):
        return False

    if m:
        return True
    if re.match(r'^(第[一二三四五六七八九十]+[章节]|[一二三四五六七八九十]+、)', s):
        return True
    return False


def main():
    ap = argparse.ArgumentParser(description='抽取需求文档纯文本')
    ap.add_argument('input')
    ap.add_argument('-o', '--output', help='输出文件，缺省打印到终端')
    ap.add_argument('--outline', action='store_true', help='只输出疑似章节标题')
    args = ap.parse_args()

    if not os.path.exists(args.input):
        sys.exit(f'找不到文件：{args.input}')

    ext = os.path.splitext(args.input)[1].lower()
    if ext == '.pdf':
        text, n = read_pdf(args.input)
        unit = '页'
    elif ext == '.docx':
        text, n = read_docx(args.input)
        unit = '段'
    elif ext in ('.txt', '.md'):
        text, n = read_plain(args.input)
        unit = '行'
    else:
        sys.exit(f'不支持的格式：{ext}（仅支持 pdf / docx / txt / md）')

    if args.outline:
        text = '\n'.join(ln.replace('\u200b', '')
                         for ln in text.split('\n') if looks_like_heading(ln))

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f'✅ 已写入 {args.output}（{n} {unit}，{len(text)} 字符）')
    else:
        print(text)


if __name__ == '__main__':
    main()

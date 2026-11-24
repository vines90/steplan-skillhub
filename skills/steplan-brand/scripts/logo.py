#!/usr/bin/env python3
"""阶梯计划 · 标志导出

    python3 logo.py list
    python3 logo.py export <版本> --width 1200 [--bg '#16171C'] [--pad 1] [-o out.png]

<版本> 为 assets/brand-kit/logo/svg 下的文件名（可省略 steplan- 前缀和 .svg），例如 logo-horizontal-reverse、mark。
--pad 以「圆点直径」为单位加安全空间（规范要求至少 1）；不给 --bg 则输出透明底 PNG。用本机 Chrome 渲染。
"""
import argparse
import pathlib
import re
import sys

SVG_DIR = pathlib.Path(__file__).resolve().parent.parent / 'assets' / 'brand-kit' / 'logo' / 'svg'


def find(name):
    for cand in (name, f'steplan-{name}', name.removesuffix('.svg'), f'steplan-{name.removesuffix(".svg")}'):
        p = SVG_DIR / (cand if cand.endswith('.svg') else cand + '.svg')
        if p.is_file():
            return p
    sys.exit(f'找不到版本 {name!r}，可用：' + '、'.join(sorted(p.stem for p in SVG_DIR.glob('*.svg'))))


def main():
    ap = argparse.ArgumentParser(description='阶梯计划 · 标志导出')
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('list', help='列出所有标志版本')
    e = sub.add_parser('export', help='导出 PNG')
    e.add_argument('name')
    e.add_argument('--width', type=int, required=True, help='标志本身的宽度（像素，不含安全空间）')
    e.add_argument('--bg', help="底色，如 '#16171C'；不给则透明")
    e.add_argument('--pad', type=float, default=0, help='四周安全空间，单位：圆点直径')
    e.add_argument('-o', '--out', type=pathlib.Path)
    a = ap.parse_args()
    if a.cmd == 'list':
        for p in sorted(SVG_DIR.glob('*.svg')):
            print(p.stem)
        return
    src = find(a.name)
    svg = src.read_text()
    vb = [float(x) for x in re.search(r'viewBox="([^"]+)"', svg)[1].split()]
    w = a.width
    h = round(w * vb[3] / vb[2])
    dot = h * 0.2 if 'horizontal' in src.stem or 'vertical' in src.stem else h * 0.14   # 圆点直径约占标志高度的比例
    pad = round(a.pad * dot)
    out = a.out or pathlib.Path(f'{src.stem}-{w}px.png')
    from playwright.sync_api import sync_playwright
    doc = (f'<html><body style="margin:0;background:{a.bg or "transparent"}">'
           f'<div id="c" style="display:inline-block;padding:{pad}px;background:{a.bg or "transparent"}">'
           f'<img src="{src.resolve().as_uri()}" style="display:block;width:{w}px;height:{h}px"></div></body></html>')
    with sync_playwright() as p:
        try:
            b = p.chromium.launch(channel='chrome')
        except Exception:
            b = p.chromium.launch()
        pg = b.new_page(viewport={'width': w + 2 * pad, 'height': h + 2 * pad})
        tmp = out.with_suffix('.tmp.html')
        tmp.write_text(doc, encoding='utf-8')
        pg.goto(tmp.resolve().as_uri())
        pg.locator('#c').screenshot(path=str(out), omit_background=not a.bg)
        tmp.unlink()
        b.close()
    print(f'{out}（{w + 2 * pad}×{h + 2 * pad}px，{"底色 " + a.bg if a.bg else "透明底"}）')


if __name__ == '__main__':
    main()

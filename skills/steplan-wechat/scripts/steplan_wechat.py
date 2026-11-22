#!/usr/bin/env python3
"""Steplan 阶梯计划 · 公众号排版渲染器

    python3 steplan_wechat.py render a.json [b.json ...] -o 输出目录 [--shots]
    python3 steplan_wechat.py blocks          列出所有块类型和字段

article.json 描述一篇文章（模板 + 块列表），渲染成带「复制到公众号」按钮的 index.html；
--shots 另外导出 预览图/*.png（需要 playwright 与本机 Chrome）。

公众号编辑器会丢掉 <style>、class、外链字体和脚本，只认写在 style 属性里的样式，
所以每个组件输出的都是纯行内样式 HTML。装饰性的点和横杠一律用块级 <section>
并塞一个 <br>（编辑器会清除空标签）；不用 position、SVG、CSS 变量和 gap。
"""
import argparse
import datetime
import html
import inspect
import json
import pathlib
import re
import sys
from html.parser import HTMLParser

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent

# ── 定稿色值（00_定稿_深空黑/色值.txt）────────────────────────────
VOID, BONE, GRAPHITE, LIME = '#16171C', '#F4F5F0', '#8A8D94', '#C8FF2E'

SANS = ("-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB',"
        "'Microsoft YaHei','Helvetica Neue',Arial,sans-serif")
MONO = "'SF Mono',Menlo,Consolas,'Courier New',monospace"
SERIF = "Georgia,'Times New Roman',serif"

# 浅色底上圆点用深空黑、不用绿色（品牌规范第 2 条）；酸性绿只做色块和深色底上的强调
LIGHT = dict(head=VOID, text='#33353B', muted=GRAPHITE, line='#E6E7E1', line2='#D3D4CD',
             card=BONE, card2='#FAFAF7', dot=VOID, inv_bg=VOID, inv_fg=LIME,
             accent=VOID, lead='#2A2C32', dim='#5C5F66')
DARK = dict(head=BONE, text='#C3C5BE', muted=GRAPHITE, line='#2E3038', line2='#43464F',
            card='#1F2027', card2='#1B1C22', dot=LIME, inv_bg=LIME, inv_fg=VOID,
            accent=LIME, lead='#DEDFD9', dim='#B4B6AF')
DIM = '#B4B6AF'  # 深色卡片里的次要正文


# ── 基础 ─────────────────────────────────────────────────────────
def esc(s):
    return html.escape(s, quote=False)


def rich(s, t):
    """行内标记：**粗体**  ==荧光色块==  [[反白色块]]  `等宽`  \\n 换行"""
    s = esc(s)
    s = re.sub(r'\*\*(.+?)\*\*', lambda m: (
        f'<strong style="font-weight:700;color:{t["head"]};">{m[1]}</strong>'), s)
    s = re.sub(r'==(.+?)==', lambda m: (
        f'<span style="background-color:{LIME};color:{VOID};font-weight:700;padding:1px 4px;">{m[1]}</span>'), s)
    s = re.sub(r'\[\[(.+?)\]\]', lambda m: (
        f'<span style="background-color:{t["inv_bg"]};color:{t["inv_fg"]};padding:0 6px;">{m[1]}</span>'), s)
    s = re.sub(r'`(.+?)`', lambda m: (
        f'<span style="font-family:{MONO};font-size:0.88em;background-color:{t["card"]};'
        f'padding:1px 5px;border-radius:3px;">{m[1]}</span>'), s)
    return s.replace('\n', '<br>')


def S(style, inner=''):
    return f'<section style="{style}">{inner}</section>'


def shape(style):
    """纯装饰块（点、横杠、方框）。"""
    return f'<section style="{style}overflow:hidden;line-height:0;font-size:0;"><br></section>'


def dot(size, color):
    return shape(f'width:{size}px;height:{size}px;border-radius:50%;background-color:{color};flex-shrink:0;')


def P(text, t, size=15, mb=18, color=None, lh=1.85, align='justify', extra=''):
    return (f'<p style="margin:0 0 {mb}px;font-size:{size}px;line-height:{lh};letter-spacing:0.5px;'
            f'color:{color or t["text"]};text-align:{align};{extra}">{rich(text, t)}</p>')


def label(text, color, size=11, ls=2, extra=''):
    return (f'<p style="margin:0;font-family:{MONO};font-size:{size}px;line-height:1.5;letter-spacing:{ls}px;'
            f'color:{color};{extra}">{esc(text)}</p>')


def stairs(lit, on, off, w=28, h=4, gap=3):
    """品牌三级横杠：上短下长、右对齐，从下往上点亮 lit 级——用作进度、难度、评分。"""
    bars = ''.join(shape(
        f'width:{round(w * (i + 1) / 3)}px;height:{h}px;margin-left:auto;margin-top:{gap if i else 0}px;'
        f'border-radius:1px;background-color:{on if 3 - i <= lit else off};') for i in range(3))
    return S(f'width:{w}px;flex-shrink:0;', bars)


def bars3(c1, c2, c3, mt=40, mb=0):
    """VI「应用元素」里的三横杠：短、中、满。"""
    return S(f'margin:{mt}px 0 {mb}px;',
             shape(f'width:30%;height:5px;border-radius:1px;background-color:{c1};')
             + shape(f'width:58%;height:5px;margin-top:5px;border-radius:1px;background-color:{c2};')
             + shape(f'width:100%;height:5px;margin-top:5px;border-radius:1px;background-color:{c3};'))


def root(inner, t, dark=False):
    skin = f'background-color:{VOID};padding:26px 18px 24px;border-radius:8px;' if dark else ''
    return (f'<section style="font-family:{SANS};font-size:15px;line-height:1.85;letter-spacing:0.5px;'
            f'color:{t["text"]};word-break:break-word;overflow-wrap:break-word;{skin}">{inner}</section>')


# ── 通用组件 ──────────────────────────────────────────────────────
def masthead(column, no, t):
    return S(f'display:flex;align-items:center;justify-content:space-between;padding-bottom:10px;'
             f'border-bottom:1px solid {t["head"]};margin-bottom:26px;',
             S('display:flex;align-items:center;',
               dot(7, t['dot'])
               + f'<p style="margin:0 0 0 8px;font-family:{MONO};font-size:11px;line-height:1.5;letter-spacing:1.5px;'
                 f'font-weight:700;color:{t["head"]};">STEPLAN 阶梯计划<span style="font-weight:400;'
                 f'color:{t["muted"]};"> — {esc(column)}</span></p>')
             + label(no, t['muted'], ls=1))


def end_mark(t):
    return S('display:flex;justify-content:center;align-items:flex-end;margin:44px 0 0;',
             stairs(3, t['head'], t['line2'], w=18, h=3, gap=2)
             + label('END', t['muted'], size=10, ls=3, extra='margin-left:8px;line-height:1;'))


def related(items, t):
    rows = ''.join(S(
        f'display:flex;align-items:baseline;padding:12px 0;border-bottom:1px solid {t["line"]};',
        f'<p style="margin:0;width:22px;flex-shrink:0;font-family:{MONO};font-size:12px;line-height:1.6;'
        f'color:{t["muted"]};">→</p>'
        f'<p style="margin:0;flex:1;font-size:14px;line-height:1.6;color:{t["head"]};">{esc(x)}</p>') for x in items)
    return S('margin:40px 0 0;',
             S(f'padding-bottom:10px;border-bottom:1px solid {t["head"]};',
               label('MORE · 往期推荐', t['head'], ls=2, extra='font-weight:700;'))
             + rows)


def footer(dark_page=False):
    body = (
        S('display:flex;align-items:center;justify-content:space-between;',
          S('display:flex;align-items:baseline;',
            f'<p style="margin:0;display:inline-block;transform:skewX(-8deg);font-size:24px;line-height:1.2;'
            f'font-weight:800;letter-spacing:-0.5px;color:{BONE};">steplan</p>'
            f'<p style="margin:0 0 0 10px;font-size:12px;line-height:1.2;letter-spacing:4px;color:{BONE};">阶梯计划</p>')
          + dot(10, LIME))
        + f'<p style="margin:22px 0 2px;font-size:18px;line-height:1.5;font-weight:800;letter-spacing:1px;'
          f'color:{BONE};">只带最核心的，去最远的地方。</p>'
        + f'<p style="margin:0;font-size:13px;line-height:1.5;font-style:italic;letter-spacing:0.3px;'
          f'color:{GRAPHITE};">Send only what matters.</p>'
        + bars3(BONE, BONE, LIME, mt=18)
        + f'<p style="margin:18px 0 0;font-size:13px;line-height:1.8;color:{DIM};">'
          f'我们是一支用 AI 重做外贸的团队，<br>这些产品已经上线：</p>'
        + S('margin-top:10px;padding:2px 12px;background-color:#1F2027;border-radius:6px;',
            ''.join(S(f'padding:11px 0;{"border-top:1px dashed #33353D;" if i else ""}',
                      S('display:flex;align-items:baseline;justify-content:space-between;',
                        f'<p style="margin:0;font-size:14.5px;line-height:1.5;font-weight:800;color:{BONE};">{name}</p>'
                        + label(url, LIME, size=12, ls=0.5, extra='margin-left:10px;'))
                      + f'<p style="margin:3px 0 0;font-size:13px;line-height:1.6;letter-spacing:0;color:{DIM};">{desc}</p>')
                    for i, (name, desc, url) in enumerate([
                        ('sohobot', '一支 AI 智能体团队，帮你找客户', 'sohobot.cc'),
                        ('Step 1', '外贸 AI 客服，一行代码嵌入独立站，免费用', 's1.steplan.io'),
                    ])))
        + S('display:flex;align-items:flex-end;justify-content:space-between;margin-top:20px;padding-top:18px;'
            'border-top:1px solid #2C2E35;',
            S('flex:1;min-width:0;',
              f'<p style="margin:0;font-size:15px;line-height:1.5;font-weight:700;color:{BONE};">关注「阶梯计划」</p>'
              f'<p style="margin:2px 0 0;font-size:13px;line-height:1.6;color:{DIM};">每周一篇 AI 外贸实战</p>')
            + label('AI × 外贸', GRAPHITE, size=10, ls=1.5, extra='margin-left:12px;flex-shrink:0;')))
    if dark_page:
        return S(f'margin-top:40px;padding-top:28px;border-top:1px solid {DARK["line"]};', body)
    return S(f'margin-top:40px;padding:24px 20px 22px;background-color:{VOID};border-radius:8px;', body)


def image_slot(caption, t, hint='图片位 · 建议宽 1080px', h=150):
    return (S(f'margin:24px 0 8px;height:{h}px;box-sizing:border-box;border:1px dashed {t["line2"]};'
              f'border-radius:6px;background-color:{t["card2"]};display:flex;flex-direction:column;'
              f'align-items:center;justify-content:center;',
              label('IMAGE', t['muted'], ls=3)
              + f'<p style="margin:4px 0 0;font-size:12px;line-height:1.5;color:{t["muted"]};">{esc(hint)}</p>')
            + f'<p style="margin:0 0 24px;font-size:12px;line-height:1.6;color:{t["muted"]};text-align:center;">'
              f'▲ {esc(caption)}</p>')


def pill(text, kind):
    """VI 里的阶段胶囊：done 已完成 / now 进行中 / todo 未开始。"""
    base = ('display:inline-block;padding:4px 12px;margin:0 6px 6px 0;border-radius:20px;font-size:12px;'
            'line-height:1.4;font-weight:700;letter-spacing:0.5px;')
    if kind == 'done':
        return (f'<span style="{base}background-color:{VOID};color:{BONE};border:1.5px solid {VOID};">'
                f'<span style="color:{LIME};font-size:10px;">●</span> {esc(text)}</span>')
    if kind == 'now':
        return f'<span style="{base}background-color:#FFFFFF;color:{VOID};border:1.5px solid {VOID};">{esc(text)}</span>'
    return f'<span style="{base}background-color:#FFFFFF;color:#A7A9AF;border:1.5px solid #D4D5CF;">{esc(text)}</span>'


# ── 01 实战干货 ──────────────────────────────────────────────────
def meta_row(cells, t):
    out = ''
    for i, (k, v) in enumerate(cells):
        sep = f'border-left:1px solid {t["line"]};padding-left:12px;' if i else ''
        out += S(f'flex:1;{sep}', label(k, t['muted'], size=10, ls=1.5) + v)
    return S(f'display:flex;padding:0 0 12px;margin-bottom:22px;border-bottom:1px solid {t["line"]};', out)


def meta_text(v, t):
    return f'<p style="margin:2px 0 0;font-size:13px;line-height:1.5;font-weight:700;color:{t["head"]};">{esc(v)}</p>'


def gets(title, items, t):
    rows = ''.join(S(
        f'display:flex;align-items:baseline;{"margin-top:8px;" if i else ""}',
        f'<p style="margin:0;width:28px;flex-shrink:0;font-family:{MONO};font-size:12px;line-height:1.7;'
        f'font-weight:700;color:{t["head"]};">{i + 1:02d}</p>'
        f'<p style="margin:0;flex:1;font-size:14.5px;line-height:1.7;color:{t["head"]};">{rich(it, t)}</p>')
        for i, it in enumerate(items))
    return S(f'background-color:{t["card"]};border-radius:6px;padding:16px 16px 18px;margin-bottom:28px;',
             label(title, t['muted'], extra='margin-bottom:10px;') + rows)


def step_head(n, total, kicker, title, t):
    return (S('display:flex;align-items:flex-end;margin:44px 0 10px;',
              stairs(n, t['head'], t['line2'])
              + label(f'STEP {n:02d} / {total:02d}' + (f' · {kicker}' if kicker else ''), t['muted'], ls=1.5,
                      extra='margin-left:10px;line-height:1;')
              + shape(f'flex:1;height:0;margin-left:10px;border-top:1px solid {t["line"]};'))
            + f'<p style="margin:0 0 16px;font-size:20px;line-height:1.45;font-weight:800;letter-spacing:0.5px;'
              f'color:{t["head"]};">{rich(title, t)}</p>')


def prompt_card(name, lines, note):
    def var(s):
        return re.sub(r'\{(.+?)\}', lambda m: f'<span style="color:{LIME};font-weight:700;">{{{m[1]}}}</span>', esc(s))
    body = ''.join(f'<p style="margin:{10 if i else 0}px 0 0;font-size:14px;line-height:1.8;letter-spacing:0.3px;'
                   f'color:#E6E7E1;text-align:left;">{var(line)}</p>' for i, line in enumerate(lines))
    return S(f'margin:24px 0 28px;background-color:{VOID};border-radius:8px;overflow:hidden;',
             S('display:flex;align-items:center;justify-content:space-between;padding:10px 16px;'
               'border-bottom:1px solid #2C2E35;',
               S('display:flex;align-items:center;',
                 dot(6, LIME) + label(f'PROMPT · {name}', LIME, ls=1.5, extra='margin-left:8px;'))
               + label('COPY', GRAPHITE, size=10, ls=2))
             + S('padding:16px 16px 18px;', body)
             + S('padding:10px 16px;background-color:#1E1F26;',
                 f'<p style="margin:0;font-size:12px;line-height:1.6;color:{GRAPHITE};">{var(note)}</p>'))


def callout(tag, text, t):
    return S(f'margin:24px 0 28px;padding:14px 16px 16px;background-color:{t["card"]};border-radius:6px;',
             f'<p style="margin:0 0 8px;line-height:1;"><span style="display:inline-block;font-size:12px;'
             f'line-height:1;font-weight:700;letter-spacing:1px;padding:5px 8px;background-color:{t["inv_bg"]};'
             f'color:{t["inv_fg"]};border-radius:3px;">{esc(tag)}</span></p>'
             + P(text, t, size=14, mb=0, lh=1.8))


def kv_list(title, rows, t):
    items = ''.join(S(
        f'display:flex;padding:11px 0;border-top:1px solid {t["line"]};',
        f'<p style="margin:0;width:92px;flex-shrink:0;font-size:13px;line-height:1.6;font-weight:700;'
        f'color:{t["head"]};">{esc(k)}</p>'
        f'<p style="margin:0;flex:1;font-size:13.5px;line-height:1.6;color:{t["text"]};">{rich(v, t)}</p>')
        for k, v in rows)
    return S(f'margin:20px 0 28px;border-bottom:1px solid {t["line"]};',
             label(title, t['muted'], extra='margin-bottom:8px;') + items)


def lime_quote(tag, text):
    on_lime = dict(LIGHT, head=VOID)
    return S(f'margin:36px 0;padding:18px 20px 24px;background-color:{LIME};border-radius:8px;',
             S('display:flex;align-items:flex-start;justify-content:space-between;',
               label(tag, VOID, ls=2, extra='font-weight:700;') + dot(26, VOID))
             + f'<p style="margin:10px 0 0;font-size:24px;line-height:1.5;font-weight:900;letter-spacing:1px;'
               f'color:{VOID};">{rich(text, on_lime)}</p>')


def checklist(title, items, t):
    rows = ''.join(S(
        f'display:flex;align-items:flex-start;padding:12px 16px;'
        f'{"border-top:1px solid " + t["line"] + ";" if i else ""}',
        shape(f'width:14px;height:14px;box-sizing:border-box;border:1.5px solid {t["head"]};border-radius:3px;'
              f'margin-top:5px;flex-shrink:0;')
        + f'<p style="margin:0 0 0 12px;flex:1;font-size:14.5px;line-height:1.7;color:{t["head"]};">{rich(it, t)}</p>')
        for i, it in enumerate(items))
    return S(f'margin:32px 0 0;border:1.5px solid {VOID};border-radius:8px;overflow:hidden;',
             S(f'display:flex;align-items:center;justify-content:space-between;padding:10px 16px;'
               f'background-color:{VOID};',
               f'<p style="margin:0;font-size:15px;line-height:1.5;font-weight:700;color:{BONE};">{esc(title)}</p>'
               + label('CHECKLIST', LIME, size=10))
             + rows)



# ── 02 深度观点（深空） ───────────────────────────────────────────
def lead_bar(text, t):
    return S(f'margin:24px 0 8px;padding:2px 0 2px 14px;border-left:2px solid {t["accent"]};',
             P(text, t, size=15.5, mb=0, color=t['lead'], lh=1.9))


def section_head(no, kicker, title, t):
    return (S('display:flex;align-items:center;margin:48px 0 12px;',
              label(no, t['accent'], size=13, ls=1, extra='font-weight:700;line-height:1;')
              + shape(f'flex:1;height:0;margin:0 12px;border-top:1px dashed {t["line2"]};')
              + label(kicker, GRAPHITE, size=10, ls=2, extra='line-height:1;'))
            + f'<p style="margin:0 0 18px;font-size:21px;line-height:1.45;font-weight:800;letter-spacing:0.5px;'
              f'color:{t['head']};">{rich(title, t)}</p>')


def stat_card(tag, big, text, t):
    return S(f'margin:28px 0;padding:20px 20px 18px;background-color:{t["card"]};border-radius:8px;',
             label(tag, GRAPHITE, ls=2)
             + f'<p style="margin:8px 0 6px;font-size:44px;line-height:1.15;font-weight:900;letter-spacing:-0.5px;'
               f'color:{t['accent']};">{esc(big)}</p>'
             + P(text, t, size=13.5, mb=0, color=t['dim'], lh=1.7, align='left'))


def pull_quote(text, source, t):
    return S(f'margin:32px 0;padding:18px 0 20px;border-top:1px solid {t["line"]};border-bottom:1px solid {t["line"]};',
             f'<p style="margin:0;height:26px;overflow:hidden;font-family:{SERIF};font-size:48px;line-height:1;'
             f'color:{t['accent']};">“</p>'
             + f'<p style="margin:4px 0 12px;font-size:19px;line-height:1.6;font-weight:800;letter-spacing:0.5px;'
               f'color:{t['head']};">{rich(text, t)}</p>'
             + label(source, GRAPHITE, ls=1))


def shift_list(pairs, t):
    """旧打法 → 新打法，逐条对照；手机上比左右双栏好读。"""
    rows = ''.join(S(
        f'display:flex;align-items:flex-start;padding:12px 0;{"border-top:1px dashed " + t["line2"] + ";" if i else ""}',
        label(f'{i + 1:02d}', t['accent'], size=11, ls=1, extra='width:30px;flex-shrink:0;font-weight:700;line-height:1.7;')
        + S('flex:1;min-width:0;',
            f'<p style="margin:0;font-size:13px;line-height:1.7;color:{GRAPHITE};text-decoration:line-through;">{esc(old)}</p>'
            f'<p style="margin:2px 0 0;font-size:15px;line-height:1.6;font-weight:700;color:{t['head']};">'
            f'<span style="color:{t['accent']};">→</span> {esc(new)}</p>'))
        for i, (old, new) in enumerate(pairs))
    return S(f'margin:24px 0 28px;padding:4px 16px 6px;background-color:{t["card"]};border-radius:8px;',
             S(f'display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid {t["line"]};',
               label('BEFORE → AFTER', GRAPHITE, size=10, ls=2) + label('旧打法 → 新打法', GRAPHITE, size=10, ls=1))
             + rows)


def ladder(steps, t):
    """三阶跃迁：顶边逐级升高，最后一阶点亮——呼应 VI 概念板「送探测器 / 送一个人 / 只送大脑」。"""
    cells = ''
    for i, (no, name, verdict) in enumerate(steps):
        last = i == len(steps) - 1
        cells += S(
            f'flex:1;min-width:0;{"margin-left:8px;" if i else ""}padding:{14 + 22 * i}px 10px 14px;'
            f'border-top:3px solid {t['accent'] if last else t["line2"]};background-color:{t["card2"]};',
            label(no, t['accent'] if last else GRAPHITE, size=11, ls=1, extra='font-weight:700;')
            + f'<p style="margin:6px 0 8px;font-size:14px;line-height:1.5;font-weight:800;'
              f'color:{t['head'] if last else "#A7A9AF"};">{esc(name)}</p>'
            + f'<p style="margin:0;font-size:12px;line-height:1.5;color:{t['accent'] if last else GRAPHITE};">{esc(verdict)}</p>')
    return S('display:flex;align-items:flex-end;margin:24px 0 28px;', cells)



# ── 03 案例战报 ──────────────────────────────────────────────────
def case_hero(title, facts, stats, badge=''):
    fact_cells = ''.join(S(
        f'flex:1;min-width:0;{"border-left:1px solid #2C2E35;padding-left:10px;" if i else ""}',
        label(k, GRAPHITE, size=10, ls=1.5)
        + f'<p style="margin:2px 0 0;font-size:13px;line-height:1.5;font-weight:700;color:{BONE};">{esc(v)}</p>')
        for i, (k, v) in enumerate(facts))
    stat_cells = ''.join(S(
        'flex:1;min-width:0;',
        f'<p style="margin:0;font-size:34px;line-height:1.1;font-weight:900;letter-spacing:-0.5px;color:{LIME};">'
        f'{esc(n)}<span style="font-size:12px;font-weight:400;letter-spacing:0;color:{BONE};margin-left:3px;">'
        f'{esc(u)}</span></p>'
        f'<p style="margin:4px 0 0;font-size:11px;line-height:1.5;color:{GRAPHITE};">{esc(k)}</p>')
        for n, u, k in stats)
    return S(f'padding:18px 18px 20px;background-color:{VOID};border-radius:8px;',
             S('display:flex;align-items:center;justify-content:space-between;',
               label('CLIENT · 客户档案', GRAPHITE, size=10, ls=2)
               + (f'<p style="margin:0;font-size:10px;line-height:1;padding:4px 6px;border:1px solid #43464F;'
                  f'border-radius:3px;color:{GRAPHITE};">{esc(badge)}</p>' if badge else ''))
             + f'<p style="margin:12px 0 16px;font-size:21px;line-height:1.45;font-weight:800;color:{BONE};">{esc(title)}</p>'
             + S('display:flex;padding-bottom:16px;border-bottom:1px solid #2C2E35;', fact_cells)
             + S('display:flex;margin-top:16px;', stat_cells))


def stepper(steps):
    """三段式进度：done 实心 / now 描边 / todo 虚线。等分宽度，手机上不会折行。"""
    cells = ''
    for i, (name, state, kind) in enumerate(steps):
        box, c1, c2 = {
            'done': (f'background-color:{VOID};border:1.5px solid {VOID};', BONE, LIME),
            'now': (f'background-color:#FFFFFF;border:1.5px solid {VOID};', VOID, GRAPHITE),
            'todo': ('background-color:#FFFFFF;border:1.5px dashed #C5C7C0;', '#A7A9AF', '#A7A9AF'),
        }[kind]
        cells += S(f'flex:1;min-width:0;box-sizing:border-box;{"margin-left:6px;" if i else ""}padding:8px 4px 9px;'
                   f'border-radius:6px;text-align:center;{box}',
                   f'<p style="margin:0;font-size:13px;line-height:1.4;font-weight:800;color:{c1};text-align:center;">{esc(name)}</p>'
                   f'<p style="margin:2px 0 0;font-size:11px;line-height:1.4;color:{c2};text-align:center;">{esc(state)}</p>')
    return S('display:flex;margin:12px 0 0;', cells)


def num_head(no, title, t):
    return S('display:flex;align-items:center;margin:40px 0 16px;',
             S(f'width:28px;height:28px;flex-shrink:0;background-color:{VOID};border-radius:4px;'
               f'display:flex;align-items:center;justify-content:center;',
               label(no, LIME, size=12, ls=0, extra='font-weight:700;line-height:1;'))
             + f'<p style="margin:0 0 0 12px;font-size:19px;line-height:1.4;font-weight:800;color:{VOID};">{esc(title)}</p>')


def timeline(stages, t):
    out = ''
    for i, (stage, when, title, text, output, kind) in enumerate(stages):
        now = kind == 'now'
        if i:
            out += shape(f'width:2px;height:16px;margin-left:24px;background-color:{t["line2"]};')
        out += S(
            f'padding:14px 16px 16px;border-radius:8px;border:{"1.5px solid " + VOID if now else "1px solid " + t["line2"]};',
            S('display:flex;align-items:center;justify-content:space-between;',
              f'<p style="margin:0;line-height:1;">{pill(stage, kind)}</p>' + label(when, t['muted'], size=11, ls=1))
            + f'<p style="margin:8px 0 6px;font-size:16px;line-height:1.5;font-weight:800;color:{VOID};">{esc(title)}</p>'
            + P(text, t, size=14, mb=0, lh=1.75)
            + S(f'margin-top:12px;padding:8px 10px;border-radius:4px;background-color:{LIME if now else t["card"]};',
                f'<p style="margin:0;font-size:12.5px;line-height:1.6;color:{VOID};">'
                f'<strong style="font-weight:800;">产出</strong>　{esc(output)}</p>'))
    return S('margin:20px 0 28px;', out)


def result_table(headers, rows, t, note=''):
    widths = ['36%', '26%', '38%']
    th = ''.join(f'<th style="width:{w};padding:10px 10px;text-align:left;font-size:12px;line-height:1.4;'
                 f'font-weight:700;letter-spacing:1px;border:none;background-color:{VOID};'
                 f'color:{LIME if i == 2 else BONE};">{esc(h)}</th>' for i, (h, w) in enumerate(zip(headers, widths)))
    td = 'padding:11px 10px;border:none;border-bottom:1px solid ' + t['line'] + ';font-size:13.5px;line-height:1.5;'
    body = ''
    for k, before, after, delta in rows:
        tag = (f' <span style="display:inline-block;font-size:11px;line-height:1.3;font-weight:800;padding:1px 5px;'
               f'border-radius:2px;background-color:{LIME};color:{VOID};">{esc(delta)}</span>') if delta else ''
        body += (f'<tr><td style="{td}font-weight:700;color:{VOID};">{esc(k)}</td>'
                 f'<td style="{td}color:{t["muted"]};">{esc(before)}</td>'
                 f'<td style="{td}font-weight:800;color:{VOID};">{esc(after)}{tag}</td></tr>')
    out = (f'<table style="width:100%;border-collapse:collapse;table-layout:fixed;margin:16px 0 8px;">'
           f'<thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>')
    if note:
        out += f'<p style="margin:0 0 24px;font-size:11px;line-height:1.6;color:{t["muted"]};">{esc(note)}</p>'
    return out


def testimonial(text, name, role, t):
    return S(f'margin:28px 0;padding:18px 18px 18px;background-color:{t["card"]};border-radius:8px;',
             f'<p style="margin:0;height:24px;overflow:hidden;font-family:{SERIF};font-size:44px;line-height:1;'
             f'color:{VOID};">“</p>'
             + P(text, t, size=15, mb=16, color=VOID, extra='font-weight:500;')
             + S('display:flex;align-items:center;',
                 S(f'width:34px;height:34px;flex-shrink:0;border-radius:50%;background-color:{VOID};'
                   f'display:flex;align-items:center;justify-content:center;',
                   f'<p style="margin:0;font-size:14px;line-height:1;font-weight:800;color:{LIME};">{esc(name[0])}</p>')
                 + S('margin-left:10px;',
                     f'<p style="margin:0;font-size:14px;line-height:1.4;font-weight:800;color:{VOID};">{esc(name)}</p>'
                     f'<p style="margin:0;font-size:12px;line-height:1.5;color:{t["muted"]};">{esc(role)}</p>')))


def actions(items, t):
    rows = ''.join(S(
        f'display:flex;align-items:flex-start;padding:14px 0;border-top:1px solid {t["line"]};',
        f'<p style="margin:0;width:44px;flex-shrink:0;font-size:28px;line-height:1;font-weight:900;'
        f'letter-spacing:-1px;color:#D4D5CF;">{i + 1:02d}</p>'
        + S('flex:1;',
            f'<p style="margin:0 0 2px;font-size:15.5px;line-height:1.5;font-weight:800;color:{VOID};">{esc(a)}</p>'
            + P(b, t, size=13.5, mb=0, lh=1.7, color='#5C5F66')))
        for i, (a, b) in enumerate(items))
    return S(f'margin:16px 0 0;border-bottom:1px solid {t["line"]};', rows)


def cta_dark(tag, title, text, button):
    return S(f'margin:36px 0 0;padding:22px 20px 24px;background-color:{VOID};border-radius:8px;',
             label(tag, LIME, ls=2)
             + f'<p style="margin:10px 0 8px;font-size:19px;line-height:1.5;font-weight:800;color:{BONE};">{esc(title)}</p>'
             + P(text, DARK, size=14, mb=18, color=DIM, lh=1.75)
             + f'<p style="margin:0;line-height:1;"><span style="display:inline-block;padding:11px 16px;'
               f'background-color:{LIME};color:{VOID};font-size:14px;line-height:1;font-weight:800;'
               f'border-radius:4px;">{esc(button)}</span></p>')



# ── 04 阶梯周刊 ──────────────────────────────────────────────────
def weekly_masthead(vol, dates, tagline):
    return S('margin-bottom:24px;',
             S('display:flex;align-items:center;justify-content:space-between;',
               S('display:flex;align-items:center;',
                 dot(7, VOID) + label('STEPLAN WEEKLY', VOID, ls=2, extra='margin-left:8px;font-weight:700;'))
               + label(vol, GRAPHITE, ls=1))
             + f'<p style="margin:12px 0 8px;font-size:40px;line-height:1.15;font-weight:900;letter-spacing:3px;'
               f'color:{VOID};">阶梯<span style="background-color:{LIME};padding:0 4px;">周刊</span></p>'
             + S('display:flex;align-items:baseline;justify-content:space-between;',
                 f'<p style="margin:0;font-size:13px;line-height:1.5;color:#5C5F66;">{esc(tagline)}</p>'
                 + label(dates, GRAPHITE, ls=0.5))
             + shape(f'height:3px;margin-top:12px;background-color:{VOID};')
             + shape(f'height:1px;margin-top:3px;background-color:{VOID};'))


def toc(items, t):
    rows = ''.join(S(
        f'display:flex;align-items:baseline;padding:8px 0;{"border-top:1px dashed #D4D5CF;" if i else ""}',
        f'<p style="margin:0;width:28px;flex-shrink:0;font-family:{MONO};font-size:12px;line-height:1.6;'
        f'font-weight:700;color:{VOID};">{i + 1:02d}</p>'
        f'<p style="margin:0;flex:1;min-width:0;font-size:14px;line-height:1.6;color:{VOID};">{esc(title)}</p>'
        + label(cat, t['muted'], size=11, ls=1, extra='margin-left:8px;flex-shrink:0;'))
        for i, (title, cat) in enumerate(items))
    return S(f'margin:0 0 8px;padding:14px 16px 8px;background-color:{t["card"]};border-radius:6px;',
             label(f'IN THIS ISSUE · 本期 {len(items)} 条', t['muted'], extra='margin-bottom:4px;') + rows)


def sec_bar(no, cn, en, count):
    return S(f'display:flex;align-items:center;justify-content:space-between;margin:36px 0 18px;'
             f'padding:10px 14px;background-color:{VOID};border-radius:4px;',
             S('display:flex;align-items:center;',
               dot(7, LIME)
               + f'<p style="margin:0 0 0 10px;font-size:15px;line-height:1.4;font-weight:800;color:{BONE};">'
                 f'<span style="font-family:{MONO};color:{LIME};">{esc(no)}</span>　{esc(cn)}'
                 f'<span style="font-family:{MONO};font-size:10px;font-weight:400;letter-spacing:2px;'
                 f'color:{GRAPHITE};">　{esc(en)}</span></p>')
             + label(count, GRAPHITE, size=10, ls=1))


def tags(items):
    return '<p style="margin:0 0 12px;line-height:1;">' + ''.join(
        f'<span style="display:inline-block;margin-right:6px;padding:4px 8px;font-size:11px;line-height:1;'
        f'color:{VOID};border:1px solid #CFD0C9;border-radius:3px;">{esc(x)}</span>' for x in items) + '</p>'


def news(no, cat, title, tag_list, body, comment, source, t):
    return S(f'padding-bottom:24px;margin-bottom:24px;border-bottom:1px solid {t["line"]};',
             label(f'{no} / {cat}', t['muted'], ls=1)
             + f'<p style="margin:4px 0 10px;font-size:17px;line-height:1.5;font-weight:800;color:{VOID};">{esc(title)}</p>'
             + tags(tag_list)
             + P(body, t, mb=14)
             + S(f'padding:12px 14px;background-color:{t["card"]};border-radius:6px;',
                 f'<p style="margin:0;font-size:14px;line-height:1.75;color:{t["text"]};text-align:justify;">'
                 f'<span style="display:inline-block;margin-right:6px;padding:3px 6px;font-size:11px;line-height:1;'
                 f'font-weight:700;letter-spacing:1px;background-color:{VOID};color:{LIME};border-radius:2px;">'
                 f'阶梯点评</span>{rich(comment, t)}</p>')
             + label(source, t['muted'], size=11, ls=0.5, extra='margin-top:10px;'))


def tool_cards(no, cat, title, tools, t):
    cards = ''.join(S(
        f'display:flex;align-items:center;padding:14px 16px;margin-top:10px;border:1px solid {t["line2"]};'
        f'border-radius:6px;',
        S('flex:1;min-width:0;',
          f'<p style="margin:0;font-size:15px;line-height:1.5;font-weight:800;color:{VOID};">{esc(name)}</p>'
          f'<p style="margin:2px 0 0;font-size:13px;line-height:1.6;color:#5C5F66;">{esc(desc)}</p>')
        + S('margin-left:14px;flex-shrink:0;display:flex;flex-direction:column;align-items:flex-end;',
            stairs(score, VOID, t['line2'], w=24)
            + label(f'实用 {score}/3', t['muted'], size=10, ls=0.5, extra='margin-top:5px;line-height:1;')))
        for name, desc, score in tools)
    return S(f'padding-bottom:24px;margin-bottom:24px;border-bottom:1px solid {t["line"]};',
             label(f'{no} / {cat}', t['muted'], ls=1)
             + f'<p style="margin:4px 0 4px;font-size:17px;line-height:1.5;font-weight:800;color:{VOID};">{esc(title)}</p>'
             + cards)


def brief(no, cat, title, text, t, last=False):
    return S(f'display:flex;align-items:flex-start;padding:14px 0;'
             f'{"" if last else "border-bottom:1px solid " + t["line"] + ";"}',
             f'<p style="margin:0;width:36px;flex-shrink:0;font-family:{MONO};font-size:13px;line-height:1.6;'
             f'font-weight:700;color:{VOID};">{esc(no)}</p>'
             + S('flex:1;min-width:0;',
                 label(cat, t['muted'], size=10, ls=1.5)
                 + f'<p style="margin:2px 0 4px;font-size:15px;line-height:1.55;font-weight:800;color:{VOID};">{esc(title)}</p>'
                 + P(text, t, size=14, mb=0, lh=1.75)))


def week_quote(no, text, t):
    return S(f'margin:40px 0 0;padding:22px 4px 24px;border-top:3px solid {VOID};border-bottom:1px solid {VOID};'
             f'text-align:center;',
             label(f'{no} · 本周一句话', t['muted'], ls=2)
             + f'<p style="margin:12px 0 0;font-size:21px;line-height:1.6;font-weight:900;letter-spacing:1px;'
               f'color:{VOID};text-align:center;">{rich(text, t)}</p>')



# ── 05 训练营招募 ─────────────────────────────────────────────────
def hero_lime(series, headline, sub):
    on_lime = dict(LIGHT, head=VOID)
    return S(f'padding:18px 20px 22px;background-color:{LIME};border-radius:8px;',
             S('display:flex;align-items:flex-start;justify-content:space-between;',
               S('display:flex;align-items:center;margin-top:4px;',
                 dot(7, VOID) + label('STEPLAN 阶梯计划 · 招募中', VOID, ls=1.5, extra='margin-left:8px;font-weight:700;'))
               + dot(40, VOID))
             + label(series, VOID, size=12, ls=1, extra='margin-top:10px;')
             + f'<p style="margin:8px 0 14px;font-size:29px;line-height:1.42;font-weight:900;letter-spacing:1px;'
               f'color:{VOID};">{rich(headline, on_lime)}</p>'
             + f'<p style="margin:0;font-size:13.5px;line-height:1.7;color:{VOID};">{esc(sub)}</p>'
             + bars3(VOID, VOID, VOID, mt=18))


def info_strip(cells):
    return S(f'display:flex;margin:10px 0 0;padding:14px 0;background-color:{VOID};border-radius:8px;',
             ''.join(S(f'flex:1;text-align:center;{"border-left:1px solid #2C2E35;" if i else ""}',
                       label(k, GRAPHITE, size=10, ls=2, extra='text-align:center;')
                       + f'<p style="margin:2px 0 0;font-size:20px;line-height:1.3;font-weight:900;color:{LIME};'
                         f'text-align:center;">{esc(v)}</p>')
                     for i, (k, v) in enumerate(cells)))


def block_head(kicker, title, t):
    return S('margin:40px 0 16px;',
             (label(kicker, t['muted'], ls=2) if kicker else '')
             + f'<p style="margin:2px 0 10px;font-size:21px;line-height:1.45;font-weight:900;letter-spacing:0.5px;'
               f'color:{t["head"]};">{esc(title)}</p>'
             + shape(f'width:28px;height:4px;border-radius:1px;background-color:{t["head"]};'))


def pains(items, t):
    return S('margin:0 0 8px;', ''.join(S(
        f'display:flex;align-items:center;padding:11px 0;border-bottom:1px dashed #D4D5CF;',
        S('width:20px;height:20px;flex-shrink:0;box-sizing:border-box;border:1.5px solid #C5C7C0;border-radius:50%;'
          'display:flex;align-items:center;justify-content:center;',
          f'<p style="margin:0;font-size:10px;line-height:1;font-weight:700;color:{GRAPHITE};">✕</p>')
        + f'<p style="margin:0 0 0 12px;flex:1;font-size:14.5px;line-height:1.6;color:{t["text"]};">{esc(it)}</p>')
        for it in items))


def stage_card(n, name, week, title, items, output, t, peak=False):
    head_bg, head_fg = (LIME, VOID) if peak else (VOID, LIME)
    bullets = ''.join(S(
        'display:flex;align-items:flex-start;margin-top:6px;',
        shape(f'width:5px;height:5px;margin-top:10px;flex-shrink:0;background-color:{VOID};')
        + f'<p style="margin:0 0 0 10px;flex:1;font-size:14px;line-height:1.75;color:{t["text"]};">{rich(it, t)}</p>')
        for it in items)
    return S(f'margin-bottom:14px;border:1.5px solid {VOID};border-radius:8px;overflow:hidden;',
             S(f'display:flex;align-items:center;justify-content:space-between;padding:10px 14px;'
               f'background-color:{head_bg};',
               f'<p style="margin:0;font-size:14px;line-height:1.4;font-weight:800;color:{head_fg};">第 {n} 阶'
               f'<span style="font-weight:400;color:{VOID if peak else GRAPHITE};"> · {esc(name)}</span></p>'
               + S('display:flex;align-items:center;',
                   label(week, VOID if peak else GRAPHITE, size=10, ls=1.5, extra='margin-right:8px;line-height:1;')
                   + stairs(n, VOID if peak else LIME, '#9FCC24' if peak else '#3A3C44', w=21, h=3, gap=2)))
             + S('padding:14px 16px 16px;',
                 f'<p style="margin:0 0 2px;font-size:16px;line-height:1.5;font-weight:800;color:{VOID};">{esc(title)}</p>'
                 + bullets
                 + S('margin-top:12px;padding-top:10px;border-top:1px dashed #D4D5CF;',
                     f'<p style="margin:0;font-size:13px;line-height:1.6;color:{VOID};">'
                     f'<span style="font-family:{MONO};font-size:10px;letter-spacing:1.5px;color:{GRAPHITE};">'
                     f'OUTPUT　</span><strong style="font-weight:800;">{esc(output)}</strong></p>')))


def fit_columns(yes, no, t):
    def col(title, items, ok, ml):
        border = f'1.5px solid {VOID}' if ok else '1px dashed #C5C7C0'
        rows = ''.join(f'<p style="margin:8px 0 0;font-size:13px;line-height:1.6;'
                       f'color:{t["text"] if ok else GRAPHITE};">{esc(it)}</p>' for it in items)
        mark = (f'<span style="display:inline-block;padding:2px 5px;margin-right:6px;font-size:11px;line-height:1.2;'
                f'background-color:{VOID if ok else "#E6E7E1"};color:{LIME if ok else GRAPHITE};border-radius:2px;">'
                f'{"✓" if ok else "✕"}</span>')
        return S(f'flex:1;min-width:0;box-sizing:border-box;{ml}padding:14px 12px 16px;border:{border};border-radius:8px;',
                 f'<p style="margin:0;font-size:15px;line-height:1.4;font-weight:800;'
                 f'color:{VOID if ok else GRAPHITE};">{mark}{esc(title)}</p>' + rows)
    return S('display:flex;align-items:stretch;margin:0 0 8px;',
             col('适合你', yes, True, '') + col('暂不适合', no, False, 'margin-left:10px;'))


def price_card(tag, price, orig, includes, note):
    rows = ''.join(f'<p style="margin:8px 0 0;font-size:14px;line-height:1.6;color:{BONE};text-align:left;">'
                   f'<span style="color:{LIME};font-weight:800;">＋</span>　{esc(it)}</p>' for it in includes)
    return S(f'margin:36px 0 0;padding:22px 20px 22px;background-color:{VOID};border-radius:8px;text-align:center;',
             label(tag, GRAPHITE, ls=2, extra='text-align:center;')
             + f'<p style="margin:8px 0 0;line-height:1.1;text-align:center;color:{LIME};">'
               f'<span style="font-size:20px;font-weight:800;">¥ </span>'
               f'<span style="font-size:44px;font-weight:900;letter-spacing:0;">{esc(price)}</span></p>'
             + f'<p style="margin:6px 0 0;font-size:12px;line-height:1.5;color:{GRAPHITE};text-align:center;'
               f'text-decoration:line-through;">{esc(orig)}</p>'
             + shape('height:1px;margin:18px 0 6px;background-color:#2C2E35;')
             + rows
             + f'<p style="margin:16px 0 0;font-size:12px;line-height:1.6;color:{GRAPHITE};text-align:center;">{esc(note)}</p>')


def faq(items, t):
    def badge(ch, solid):
        return S(f'width:22px;height:22px;flex-shrink:0;box-sizing:border-box;border-radius:4px;'
                 f'border:1.5px solid {VOID};background-color:{VOID if solid else "#FFFFFF"};'
                 f'display:flex;align-items:center;justify-content:center;',
                 label(ch, LIME if solid else VOID, size=12, ls=0, extra='font-weight:700;line-height:1;'))
    out = ''
    for i, (q, a) in enumerate(items):
        out += S(f'padding:14px 0;{"border-top:1px solid " + t["line"] + ";" if i else ""}',
                 S('display:flex;align-items:flex-start;',
                   badge('Q', True)
                   + f'<p style="margin:0 0 0 10px;flex:1;font-size:15px;line-height:1.5;font-weight:800;color:{VOID};">{esc(q)}</p>')
                 + S('display:flex;align-items:flex-start;margin-top:8px;',
                     badge('A', False)
                     + f'<p style="margin:0 0 0 10px;flex:1;font-size:14px;line-height:1.7;color:{t["text"]};">{esc(a)}</p>'))
    return S(f'border-bottom:1px solid {t["line"]};', out)


def join_cta(how, text, urgent):
    return S(f'margin:36px 0 0;padding:18px 18px 20px;border:1.5px solid {VOID};border-radius:8px;',
             label('HOW TO JOIN · 报名方式', GRAPHITE, ls=2)
             + f'<p style="margin:8px 0 6px;font-size:19px;line-height:1.5;font-weight:900;color:{VOID};">{rich(how, LIGHT)}</p>'
             + f'<p style="margin:0 0 14px;font-size:13.5px;line-height:1.7;color:#5C5F66;">{esc(text)}</p>'
             + (f'<p style="margin:0;line-height:1;"><span style="display:inline-block;padding:5px 8px;font-size:12px;'
                f'line-height:1;font-weight:800;background-color:{VOID};color:{LIME};border-radius:3px;">{esc(urgent)}</span></p>'
                if urgent else ''))


# ── 模板 ─────────────────────────────────────────────────────────
TEMPLATES = {
    'sop': dict(name='实战干货', en='STEP SOP', dark=False, swatch=['#FFFFFF', VOID, LIME],
                fit='教程 · SOP · 工具用法',
                desc='白底为主，STEP 阶梯标题显示进度，深空黑提示词卡片可直接复制，结尾行动清单。'),
    'essay': dict(name='深度观点', en='DEEP SPACE', dark=True, swatch=[VOID, BONE, LIME],
                  fit='行业观察 · 品牌长文 · 创始人随笔',
                  desc='全篇深空黑，酸性绿只点在编号和关键词上；三阶跃迁图呼应品牌故事。'),
    'case': dict(name='案例战报', en='CASE REPORT', dark=False, swatch=[VOID, LIME, BONE],
                 fit='客户案例 · 学员成果 · 项目复盘',
                 desc='深色数据头卡 + 三段进度 + 阶段时间线 + 前后对比表，结尾引导转化。'),
    'weekly': dict(name='阶梯周刊', en='WEEKLY', dark=False, swatch=['#FFFFFF', VOID, BONE],
                   fit='周报 · 资讯合集 · 工具速递',
                   desc='报头 + 目录 + 分栏黑条，每条资讯配「阶梯点评」，工具用三横杠打分。'),
    'camp': dict(name='招募发布', en='ACID LIME', dark=False, swatch=[LIME, VOID, '#FFFFFF'],
                 fit='训练营招生 · 活动报名 · 产品发布',
                 desc='酸性绿主视觉开场，三阶课程卡、适合人群、价格卡、FAQ、报名方式。'),
}

# ── 块注册表：article.json 里的 type → 组件 ─────────────────────────
BLOCKS = {}


def block(fn):
    BLOCKS[fn.__name__[2:]] = fn
    return fn


# 通用
@block
def b_p(t, text, size=15):
    """正文段落"""
    return P(text, t, size=size)


@block
def b_bullets(t, items):
    """通用列表（方块圆点）"""
    rows = ''.join(S(
        f'display:flex;align-items:flex-start;{"margin-top:6px;" if i else ""}',
        shape(f'width:5px;height:5px;margin-top:11px;flex-shrink:0;background-color:{t["head"]};')
        + f'<p style="margin:0 0 0 10px;flex:1;font-size:15px;line-height:1.85;letter-spacing:0.5px;'
          f'color:{t["text"]};text-align:justify;">{rich(it, t)}</p>')
        for i, it in enumerate(items))
    return S('margin:0 0 18px;', rows)


@block
def b_image(t, caption, hint='图片位 · 建议宽 1080px', height=150):
    """图片位（虚线框，粘贴后在编辑器里换成真图）+ 图注"""
    return image_slot(caption, t, hint=hint, h=height)


@block
def b_masthead(t, column, no):
    """报头：● STEPLAN 阶梯计划 — 栏目 / 期号"""
    return masthead(column, no, t)


@block
def b_blockhead(t, title, kicker=''):
    """小标题：英文小字 + 大标题 + 短横杠"""
    return block_head(kicker, title, t)


@block
def b_end(t):
    """正文结束标记（三横杠 + END）"""
    return end_mark(t)


@block
def b_related(t, items):
    """往期推荐"""
    return related(items, t)


# 实战干货
@block
def b_meta(t, read, level, level_text, fit):
    """阅读时长 / 难度（1–3 级横杠）/ 适合人群"""
    return meta_row([
        ('阅读', meta_text(read, t)),
        ('难度', S('display:flex;align-items:center;margin-top:4px;',
                 stairs(level, t['head'], t['line2'], w=21, h=3, gap=2)
                 + f'<p style="margin:0 0 0 8px;font-size:13px;line-height:1.5;font-weight:700;'
                   f'color:{t["head"]};">{esc(level_text)}</p>')),
        ('适合', meta_text(fit, t)),
    ], t)


@block
def b_gets(t, items, title='YOU WILL GET · 读完你将得到'):
    """读完你将得到（编号清单卡）"""
    return gets(title, items, t)


@block
def b_step(t, n, total, title, kicker=''):
    """STEP 标题，三级横杠点亮 n 级"""
    return step_head(n, total, kicker, title, t)


@block
def b_prompt(t, name, lines, note='把 {…} 换成你的真实信息'):
    """提示词卡片，{变量} 标绿"""
    return prompt_card(name, lines, note)


@block
def b_callout(t, text, tag='注意'):
    """提示框：黑底绿字标签 + 说明"""
    return callout(tag, text, t)


@block
def b_kv(t, title, rows):
    """键值清单（筛选标准、参数）"""
    return kv_list(title, rows, t)


@block
def b_keypoint(t, text, tag='KEY POINT · 划重点'):
    """酸性绿金句卡"""
    return lime_quote(tag, text)


@block
def b_checklist(t, title, items):
    """行动清单（勾选框）"""
    return checklist(title, items, t)


# 深度观点
@block
def b_kicker(t, text):
    """开场小字"""
    return label(text, t['accent'], size=11, ls=1, extra='margin-bottom:12px;')


@block
def b_headline(t, text):
    """开场大字（28px）"""
    return (f'<p style="margin:0 0 16px;font-size:28px;line-height:1.45;font-weight:900;letter-spacing:1px;'
            f'color:{t["head"]};">{rich(text, t)}</p>')


@block
def b_byline(t, text):
    """署名行"""
    return label(text, GRAPHITE, ls=1)


@block
def b_lead(t, text):
    """导语（左侧强调竖线）"""
    return lead_bar(text, t)


@block
def b_section(t, no, kicker, title):
    """章节标题：编号 + 虚线 + 英文小字 + 标题"""
    return section_head(no, kicker, title, t)


@block
def b_stat(t, big, text, tag='A NUMBER · 一个数字'):
    """一个大数字 + 说明"""
    return stat_card(tag, big, text, t)


@block
def b_pullquote(t, text, source='—— 阶梯计划'):
    """引述金句"""
    return pull_quote(text, source, t)


@block
def b_shift(t, pairs):
    """旧打法 → 新打法 逐条对照"""
    return shift_list(pairs, t)


@block
def b_ladder(t, steps):
    """三阶跃迁（逐级升高，最后一阶点亮）"""
    return ladder(steps, t)


@block
def b_epilogue(t, text, tag='EPILOGUE · 结语'):
    """结语大字"""
    return S('margin:44px 0 0;',
             label(tag, GRAPHITE, ls=2)
             + f'<p style="margin:10px 0 0;font-size:22px;line-height:1.6;font-weight:900;letter-spacing:1px;'
               f'color:{t["head"]};">{rich(text, t)}</p>')


# 案例战报
@block
def b_case_hero(t, title, facts, stats, badge=''):
    """深色数据头卡：facts=[[键,值]]，stats=[[数字,单位,说明]]"""
    return case_hero(title, facts, stats, badge)


@block
def b_stepper(t, steps):
    """三段进度：[[名称,状态,done|now|todo]]"""
    return stepper(steps)


@block
def b_numhead(t, no, title):
    """编号方块标题"""
    return num_head(no, title, t)


@block
def b_timeline(t, stages):
    """阶段时间线：[{stage,when,title,text,output,kind}]"""
    return timeline([(s['stage'], s['when'], s['title'], s['text'], s['output'], s.get('kind', 'done'))
                     for s in stages], t)


@block
def b_table(t, headers, rows, note=''):
    """三列对比表：headers=[指标,之前,之后]，rows=[[指标,之前,之后,涨幅?]]"""
    return result_table(headers, [(list(r) + [''])[:4] for r in rows], t, note)


@block
def b_testimonial(t, text, name, role):
    """客户证言"""
    return testimonial(text, name, role, t)


@block
def b_actions(t, items):
    """大编号要点：[[标题,说明]]"""
    return actions(items, t)


@block
def b_cta(t, title, text, button, tag='NEXT · 下一步'):
    """深色转化卡 + 绿色按钮"""
    return cta_dark(tag, title, text, button)


# 阶梯周刊
@block
def b_weekly_masthead(t, vol, dates, tagline='AI × 外贸 · 每周一份可执行情报'):
    """周刊报头"""
    return weekly_masthead(vol, dates, tagline)


@block
def b_toc(t, items):
    """本期目录：[[标题,分类]]"""
    return toc(items, t)


@block
def b_secbar(t, no, cn, en, count):
    """分栏黑条"""
    return sec_bar(no, cn, en, count)


@block
def b_news(t, no, cat, title, body, comment, source, tags=()):
    """资讯条目 + 阶梯点评"""
    return news(no, cat, title, list(tags), body, comment, source, t)


@block
def b_tools(t, no, cat, title, tools):
    """工具卡：[[名称,一句话,评分1-3]]"""
    return tool_cards(no, cat, title, tools, t)


@block
def b_briefs(t, items):
    """简讯列表：[{no,cat,title,text}]"""
    return ''.join(brief(it['no'], it['cat'], it['title'], it['text'], t, last=i == len(items) - 1)
                   for i, it in enumerate(items))


@block
def b_weekquote(t, no, text):
    """本周一句话"""
    return week_quote(no, text, t)


# 招募发布
@block
def b_hero_lime(t, series, headline, sub):
    """酸性绿主视觉"""
    return hero_lime(series, headline, sub)


@block
def b_info(t, cells):
    """黑底信息条：[[标签,值]] × 3"""
    return info_strip(cells)


@block
def b_pains(t, items):
    """痛点列表（✕）"""
    return pains(items, t)


@block
def b_stage(t, n, name, week, title, items, output, peak=False):
    """课程阶段卡；peak=true 用酸性绿表头"""
    return stage_card(n, name, week, title, items, output, t, peak=peak)


@block
def b_fit(t, yes, no):
    """适合 / 不适合 两栏"""
    return fit_columns(yes, no, t)


@block
def b_price(t, price, orig, includes, note='价格与权益以报名页为准', tag='EARLY BIRD · 早鸟价'):
    """价格卡"""
    return price_card(tag, price, orig, includes, note)


@block
def b_faq(t, items):
    """问答：[[问,答]]"""
    return faq(items, t)


@block
def b_join(t, how, text, urgent=''):
    """报名方式（不放二维码）"""
    return join_cta(how, text, urgent)


def params(fn):
    out = []
    for name, prm in list(inspect.signature(fn).parameters.items())[1:]:
        out.append(name if prm.default is inspect.Parameter.empty else f'{name}={prm.default!r}')
    return ', '.join(out)


# ── 渲染与检查 ───────────────────────────────────────────────────
def render_article(spec, src):
    tpl = spec.get('template')
    if tpl not in TEMPLATES:
        sys.exit(f'{src}：template 必须是 {" / ".join(TEMPLATES)}，现在是 {tpl!r}')
    dark = TEMPLATES[tpl]['dark']
    t = DARK if dark else LIGHT
    out = ''
    for i, b in enumerate(spec.get('blocks', []), 1):
        b = {'type': 'p', 'text': b} if isinstance(b, str) else dict(b)
        kind = b.pop('type', None)
        fn = BLOCKS.get(kind)
        if not fn:
            sys.exit(f'{src} 第 {i} 块：未知类型 {kind!r}\n可用：{", ".join(BLOCKS)}')
        try:
            out += fn(t, **b)
        except (TypeError, KeyError, ValueError, IndexError) as e:
            sys.exit(f'{src} 第 {i} 块（{kind}）字段有误：{e!r}\n需要：{kind}({params(fn)})')
    if spec.get('footer', True):
        out += footer(dark_page=dark)
    return root(out, t, dark=dark)


class _Nesting(HTMLParser):
    BLOCK = {'p', 'section', 'div', 'table', 'ul', 'ol', 'h1', 'h2', 'h3', 'blockquote'}
    VOID_TAGS = {'br', 'img', 'hr'}

    def __init__(self):
        super().__init__()
        self.stack, self.errors = [], []

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID_TAGS:
            return
        if tag in self.BLOCK and 'p' in self.stack:
            self.errors.append(f'<{tag}> 嵌在 <p> 里（浏览器会拆开，样式会错）')
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.stack:
            while self.stack and self.stack.pop() != tag:
                pass


def lint(article_html):
    """公众号编辑器会丢弃或破坏的写法。"""
    problems = [f'含有 {name}' for pat, name in [
        ('class=', 'class 属性'), (' id=', 'id 属性'), ('position:', 'position 定位'), ('<svg', 'SVG'),
        ('var(--', 'CSS 变量'), ('<style', '<style> 标签'), ('<script', '脚本'), ('<p></p>', '空段落'),
    ] if pat in article_html]
    if re.search(r'[;"]gap:', article_html):
        problems.append('含有 gap（老版本微信不支持）')
    checker = _Nesting()
    checker.feed(article_html)
    return problems + sorted(set(checker.errors))


PAGE = r'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__PAGE_TITLE__</title>
<style>
@font-face{font-family:Unbounded;src:url(__FONTS__/Unbounded.ttf)}
@font-face{font-family:Smiley;src:url(__FONTS__/SmileySans.ttf)}
@font-face{font-family:JBM;src:url(__FONTS__/JetBrainsMono.ttf)}
*{box-sizing:border-box}
html,body{margin:0}
body{background:#0E0F13;color:#F4F5F0;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC',sans-serif}
button{font:inherit}
.top{display:flex;align-items:center;justify-content:space-between;padding:16px 28px;border-bottom:1px solid #24252B}
.brand{display:flex;align-items:baseline;gap:12px}
.brand b{font-family:Unbounded;font-weight:600;font-size:20px;transform:skewX(-8deg);display:inline-block;letter-spacing:-.5px}
.brand span{font-family:Smiley;font-size:17px;letter-spacing:2px;color:#C3C5BE}
.brand i{width:8px;height:8px;border-radius:50%;background:#C8FF2E;display:inline-block;transform:translateY(-2px)}
.top small{font-family:JBM;font-size:11px;letter-spacing:2px;color:#8A8D94}
.layout{display:grid;grid-template-columns:320px 1fr;align-items:start}
aside{position:sticky;top:0;height:100vh;overflow:auto;padding:20px 16px 40px;border-right:1px solid #24252B}
.cap{font-family:JBM;font-size:10px;letter-spacing:2px;color:#8A8D94;margin:4px 6px 12px}
.tpl-btn{display:block;width:100%;text-align:left;background:none;border:1px solid transparent;border-radius:10px;padding:14px 14px 14px 16px;color:inherit;cursor:pointer;margin-bottom:6px;position:relative}
.tpl-btn:hover{background:#16171C}
.tpl-btn.on{background:#1A1B21;border-color:#2E3038}
.tpl-btn.on::before{content:"";position:absolute;left:0;top:16px;bottom:16px;width:3px;border-radius:2px;background:#C8FF2E}
.tpl-btn .no{font-family:JBM;font-size:10px;letter-spacing:2px;color:#8A8D94}
.tpl-btn.on .no{color:#C8FF2E}
.tpl-btn .name{font-family:Smiley;font-size:22px;letter-spacing:1px;margin:2px 0 2px}
.tpl-btn .fit{font-size:12px;color:#C3C5BE}
.tpl-btn .desc{font-size:12px;line-height:1.65;color:#8A8D94;margin-top:6px}
.sw{display:flex;gap:4px;margin-top:10px}
.sw span{width:16px;height:16px;border-radius:4px;border:1px solid #33353D}
.notes{margin:24px 6px 0;padding-top:16px;border-top:1px solid #24252B;font-size:12px;line-height:1.8;color:#8A8D94}
.notes b{color:#C3C5BE;font-weight:600}
.stage{display:flex;flex-direction:column;align-items:center;padding:0 24px 80px;min-width:0}
.bar{position:sticky;top:0;z-index:5;width:100%;display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:center;padding:14px 0;background:rgba(14,15,19,.88);backdrop-filter:blur(10px)}
.seg{display:inline-flex;border:1px solid #2E3038;border-radius:9px;overflow:hidden}
.seg button{background:none;border:0;color:#8A8D94;padding:8px 14px;font-size:13px;cursor:pointer}
.seg button.on{background:#24252B;color:#F4F5F0}
.btn{border-radius:9px;padding:9px 16px;font-size:13px;font-weight:700;cursor:pointer;border:1px solid #2E3038}
.btn.primary{background:#C8FF2E;border-color:#C8FF2E;color:#16171C}
.btn.ghost{background:#16171C;color:#F4F5F0}
.status{width:100%;text-align:center;font-size:12px;color:#C8FF2E;min-height:18px;margin-top:-4px}
.device{width:375px;background:#fff;color:#000;border-radius:32px;overflow:hidden;margin-top:8px;box-shadow:0 0 0 10px #1A1B21,0 0 0 11px #2E3038,0 30px 80px rgba(0,0,0,.5);transition:width .25s}
.device.pc{width:741px;border-radius:12px;box-shadow:0 0 0 1px #2E3038,0 30px 80px rgba(0,0,0,.5)}
.wx-head{padding:28px 16px 4px}
.device.pc .wx-head,.device.pc .wx-body{padding-left:32px;padding-right:32px}
.wx-title{font-size:22px;line-height:1.4;font-weight:700;color:rgba(0,0,0,.9);margin:0 0 14px}
.wx-meta{font-size:15px;color:rgba(0,0,0,.3);margin-bottom:22px}
.wx-meta em{font-style:normal;color:#576B95;margin-right:8px}
.wx-body{padding:0 16px 48px}
.tpl{display:none}
.tpl.on{display:block}
.single .layout{display:block}
.single aside{display:none}
.shot .top,.shot aside,.shot .bar,.shot .status{display:none}
.shot .layout{display:block}
.shot .stage{padding:0}
.shot .device{margin:0;border-radius:0;box-shadow:none}
@media (max-width:900px){
  .layout{grid-template-columns:1fr}
  aside{position:static;height:auto;border-right:0;border-bottom:1px solid #24252B;display:flex;overflow-x:auto;gap:8px;padding:12px}
  .cap,.notes,.tpl-btn .desc{display:none}
  .tpl-btn{min-width:150px;margin:0}
  .device{width:100%;max-width:375px}
}
</style>
</head>
<body class="__BODY_CLASS__">
<header class="top">
  <div class="brand"><i></i><b>steplan</b><span>阶梯计划 · 公众号排版</span></div>
  <small>__COUNT__ · WECHAT READY</small>
</header>
<div class="layout">
  <aside>
    <div class="cap">ARTICLES · 选择文章</div>
    __NAV__
    <div class="notes">
      <b>怎么用</b><br>
      点「复制到公众号」→ 在公众号后台正文里粘贴 → 改文字、把虚线图片位换成真图。<br><br>
      <b>深色模式</b>：发布前用手机预览，打开系统深色模式再看一遍。
    </div>
  </aside>
  <main class="stage">
    <div class="bar">
      <div class="seg" id="seg"><button data-w="m" class="on">手机预览</button><button data-w="pc">电脑预览</button></div>
      <button class="btn primary" id="copy">复制到公众号</button>
      <button class="btn ghost" id="copySrc">复制 HTML 源码</button>
    </div>
    <div class="status" id="status"></div>
    <div class="device" id="device">
      <div class="wx-head">
        <h1 class="wx-title" id="wxTitle"></h1>
        <div class="wx-meta"><em>阶梯计划</em><span id="wxDate"></span></div>
      </div>
      <div class="wx-body">
        __ARTICLES__
      </div>
    </div>
  </main>
</div>
<script>
const META = __META__;
const tpls = [...document.querySelectorAll('.tpl')];
const btns = [...document.querySelectorAll('.tpl-btn')];
const status = document.getElementById('status');
let cur = 0;
function show(i) {
  cur = i;
  tpls.forEach((el, k) => el.classList.toggle('on', k === i));
  btns.forEach((el, k) => el.classList.toggle('on', k === i));
  document.getElementById('wxTitle').textContent = META[i].title;
  document.getElementById('wxDate').textContent = META[i].date;
  status.textContent = '';
  history.replaceState(null, '', '#' + (i + 1));
}
btns.forEach((b, i) => b.addEventListener('click', () => show(i)));
document.getElementById('seg').addEventListener('click', e => {
  const w = e.target.dataset.w; if (!w) return;
  [...e.currentTarget.children].forEach(b => b.classList.toggle('on', b === e.target));
  document.getElementById('device').classList.toggle('pc', w === 'pc');
});
function flash(msg) { status.textContent = msg; }
document.getElementById('copy').addEventListener('click', async () => {
  const node = tpls[cur];
  const html = node.innerHTML, text = node.innerText;
  try {
    await navigator.clipboard.write([new ClipboardItem({
      'text/html': new Blob([html], {type: 'text/html'}),
      'text/plain': new Blob([text], {type: 'text/plain'}),
    })]);
    flash('已复制「' + META[cur].name + '」，到公众号后台正文区粘贴即可');
  } catch {
    const range = document.createRange(); range.selectNodeContents(node);
    const sel = getSelection(); sel.removeAllRanges(); sel.addRange(range);
    document.execCommand('copy'); sel.removeAllRanges();
    flash('已用兼容模式复制「' + META[cur].name + '」');
  }
});
document.getElementById('copySrc').addEventListener('click', async () => {
  const html = tpls[cur].innerHTML;
  try { await navigator.clipboard.writeText(html); }
  catch {
    const ta = document.createElement('textarea'); ta.value = html; document.body.appendChild(ta);
    ta.select(); document.execCommand('copy'); ta.remove();
  }
  flash('已复制 HTML 源码（适合 135 / 秀米等编辑器的 HTML 模式）');
});
const n = parseInt(location.hash.slice(1), 10);
show(n >= 1 && n <= tpls.length ? n - 1 : 0);
</script>
</body>
</html>
'''


def build_page(specs, out_dir):
    today = datetime.date.today()
    nav, arts, meta, ok = '', '', [], True
    for i, (src, spec) in enumerate(specs):
        info = TEMPLATES.get(spec.get('template'), {})
        article = render_article(spec, src)
        for problem in lint(article):
            ok = False
            print(f'⚠ {src}：{problem}')
        name = spec.get('name') or info['name']
        nav += (f'<button class="tpl-btn"><div class="no">{i + 1:02d} · {info["en"]}</div>'
                f'<div class="name">{esc(name)}</div><div class="fit">{esc(spec.get("fit") or info["fit"])}</div>'
                f'<div class="desc">{esc(spec.get("desc") or info["desc"])}</div>'
                f'<div class="sw">{"".join(f"<span style=background:{c}></span>" for c in info["swatch"])}</div></button>')
        arts += f'<div class="tpl">{article}</div>'
        meta.append(dict(name=name, title=spec.get('title', name),
                         date=spec.get('date') or f'{today.year}年{today.month}月{today.day}日'))
    single = len(specs) == 1
    page = (PAGE.replace('__NAV__', nav).replace('__ARTICLES__', arts)
            .replace('__META__', json.dumps(meta, ensure_ascii=False))
            .replace('__COUNT__', '1 ARTICLE' if single else f'{len(specs)} ARTICLES')
            .replace('__BODY_CLASS__', 'single' if single else '')
            .replace('__PAGE_TITLE__', esc(meta[0]['title'] if single else '阶梯计划 · 公众号排版'))
            .replace('__FONTS__', (SKILL_DIR / 'assets' / 'fonts').as_uri()))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'index.html').write_text(page, encoding='utf-8')
    print(f'{"✓" if ok else "⚠"} {out_dir / "index.html"}（{len(specs)} 篇）')
    return [m['name'] for m in meta]


def shots(out_dir, names):
    from playwright.sync_api import sync_playwright
    shot_dir = out_dir / '预览图'
    slice_dir = shot_dir / '切片'
    shot_dir.mkdir(exist_ok=True)
    slice_dir.mkdir(exist_ok=True)
    for old in slice_dir.glob('*.png'):
        old.unlink()
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel='chrome')
        except Exception:
            browser = p.chromium.launch()
        pg = browser.new_page(viewport={'width': 375, 'height': 800}, device_scale_factor=2)
        pg.goto((out_dir / 'index.html').resolve().as_uri())
        pg.evaluate('document.body.classList.add("shot")')
        for i, name in enumerate(names):
            pg.evaluate(f'show({i})')
            pg.wait_for_timeout(200)
            path = shot_dir / f'{i + 1:02d}-{name}.png'
            device = pg.locator('#device')
            device.screenshot(path=str(path))
            print('预览图：', path)
            box = device.bounding_box()
            for k, top in enumerate(range(0, int(box['height']), 1000), 1):
                clip = dict(x=box['x'], y=box['y'] + top, width=box['width'],
                            height=min(1000, box['height'] - top))
                pg.screenshot(path=str(slice_dir / f'{i + 1:02d}-{name}-{k}.png'), clip=clip, full_page=True)
        browser.close()


def main():
    ap = argparse.ArgumentParser(description='Steplan 阶梯计划 · 公众号排版')
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('render', help='article.json → index.html')
    r.add_argument('specs', nargs='+', type=pathlib.Path)
    r.add_argument('-o', '--out', type=pathlib.Path, help='输出目录（默认：第一个 json 所在目录）')
    r.add_argument('--shots', action='store_true', help='同时导出手机长截图')
    sub.add_parser('blocks', help='列出所有块类型和字段')
    args = ap.parse_args()

    if args.cmd == 'blocks':
        for name, fn in BLOCKS.items():
            print(f'{name}({params(fn)})  — {fn.__doc__}')
        return
    specs = []
    for path in args.specs:
        try:
            specs.append((path.name, json.loads(path.read_text(encoding='utf-8'))))
        except json.JSONDecodeError as e:
            sys.exit(f'{path}：JSON 格式错误：{e}')
    out_dir = (args.out or args.specs[0].parent).resolve()
    names = build_page(specs, out_dir)
    if args.shots:
        shots(out_dir, names)


if __name__ == '__main__':
    main()

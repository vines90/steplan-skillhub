#!/usr/bin/env python3
"""Steplan 阶梯计划 · 海报生成器

    python3 steplan_poster.py render a.json [b.json ...] [-o 输出目录] [--scale 3]
    python3 steplan_poster.py fields        列出模板和字段

poster.json 描述一张海报（模板 + 文案），渲染成 PNG（默认 2 倍分辨率，手机上不糊）：
  course                 → 课程长图（宽 1080、高度随内容）与 9:16 单屏，含大纲、讲师、报名二维码
  camp / product / quote → 竖版 9:16（1080×1920）与小红书 3:4（1080×1440），可用 sizes 选择
  cover                  → 公众号封面 2.35:1、公众号次图 1:1、小红书封面 3:4
二维码：signup.qr 给图片路径，或 signup.qr_url 给链接自动生成（内置 segno）。
品牌字体随技能打包，用本机 Chrome（playwright）渲染，不需要安装字体。
"""
import argparse
import html
import json
import pathlib
import re
import sys
import tempfile

SKILL = pathlib.Path(__file__).resolve().parent.parent
ASSETS = SKILL / 'assets'

VOID, BONE, GRAPHITE, LIME = '#16171C', '#F4F5F0', '#8A8D94', '#C8FF2E'
POSTER_SIZES = {'9:16': (1080, 1920), '3:4': (1080, 1440), 'long': (1080, None)}
COVER_SIZES = {'公众号封面': (900, 383), '公众号次图': (500, 500), '小红书封面': (1080, 1440)}


def uri(rel):
    return (ASSETS / rel).resolve().as_uri()


def esc(s):
    return html.escape(str(s), quote=False)


def rich(s):
    """[[反白色块]]  ==酸性绿色块==  **粗体**  \\n 换行"""
    s = esc(s)
    s = re.sub(r'\[\[(.+?)\]\]', r'<span class="hl">\1</span>', s)
    s = re.sub(r'==(.+?)==', r'<span class="mk">\1</span>', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    return s.replace('\n', '<br>')


def local(path):
    return pathlib.Path(path).expanduser().resolve().as_uri()


def qr_html(signup, cls='qr'):
    """报名二维码：图片路径 > 链接自动生成 > 占位框。"""
    if signup.get('qr'):
        return f'<div class="{cls}"><img src="{local(signup["qr"])}"></div>'
    if signup.get('qr_url'):
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / '_vendor'))
        import segno
        rows = [list(r) for r in segno.make(signup['qr_url'], error='m', micro=False).matrix]
        n, d = len(rows), ''
        for y, r in enumerate(rows):          # 同一行相邻码点合并成矩形，放大后不出缝
            x = 0
            while x < n:
                if r[x]:
                    w = 1
                    while x + w < n and r[x + w]:
                        w += 1
                    d += f'M{x} {y}h{w}v1h-{w}z'
                    x += w
                else:
                    x += 1
        return (f'<div class="{cls}"><svg viewBox="0 0 {n} {n}" shape-rendering="crispEdges">'
                f'<path fill="#16171C" d="{d}"/></svg></div>')
    return f'<div class="{cls} qr-ph"><span>QR CODE<br>报名二维码</span></div>'


def photo_html(t, cls='photo'):
    if t.get('photo'):
        return f'<img class="{cls}" src="{local(t["photo"])}">'
    return f'<div class="{cls} ph-ph">{esc(t.get("name", "?")[:1])}</div>'


def need(spec, *keys):
    miss = [k for k in keys if not spec.get(k)]
    if miss:
        raise ValueError(f'缺少字段：{", ".join(miss)}')


# ── 样式 ─────────────────────────────────────────────────────────
CSS = """
@font-face{font-family:Display;src:url(%(f)s/SmileySans.ttf)}
@font-face{font-family:Sans;src:url(%(f)s/NotoSansSC.ttf);font-weight:100 900}
@font-face{font-family:Mono;src:url(%(f)s/JetBrainsMono.ttf);font-weight:100 800}
@font-face{font-family:Wide;src:url(%(f)s/Unbounded.ttf);font-weight:200 900}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:#555}
#poster{position:relative;overflow:hidden;display:flex;flex-direction:column;background:var(--bg);color:var(--fg);
  font-family:Sans,'PingFang SC',sans-serif;font-weight:400;-webkit-font-smoothing:antialiased}
.t-dark{--bg:#16171C;--fg:#F4F5F0;--dim:#B4B6AF;--muted:#8A8D94;--card:#1F2027;--cardfg:#F4F5F0;--line:#2E3038;
  --dot:#C8FF2E;--hlbg:#C8FF2E;--hlfg:#16171C;--acc:#C8FF2E;--peak:#C8FF2E;--peakfg:#16171C}
.t-lime{--bg:#C8FF2E;--fg:#16171C;--dim:#2B3112;--muted:#4D5A16;--card:#16171C;--cardfg:#F4F5F0;--line:rgba(22,23,28,.22);
  --dot:#16171C;--hlbg:#16171C;--hlfg:#C8FF2E;--acc:#16171C;--peak:#F4F5F0;--peakfg:#16171C}
.t-bone{--bg:#F4F5F0;--fg:#16171C;--dim:#33353B;--muted:#8A8D94;--card:#FFFFFF;--cardfg:#16171C;--line:#DCDDD6;
  --dot:#16171C;--hlbg:#C8FF2E;--hlfg:#16171C;--acc:#16171C;--peak:#16171C;--peakfg:#C8FF2E}
.display{font-family:Display;font-weight:400}
.mono{font-family:Mono,Sans,monospace;letter-spacing:.14em}
.hl{background:var(--hlbg);color:var(--hlfg);padding:0 .12em;-webkit-box-decoration-break:clone}
.mk{background:#C8FF2E;color:#16171C;padding:0 .1em}
.t-lime .mk{background:#16171C;color:#C8FF2E}
b{font-weight:700}
.head{flex:none;display:flex;justify-content:space-between;align-items:center;position:relative;z-index:2}
.logo{height:50px;display:block}
.tag{font-family:Mono,Sans;font-size:22px;letter-spacing:.12em;line-height:1;padding:12px 20px;border-radius:40px;
  border:2px solid currentColor;font-weight:600}
.foot{flex:none;display:flex;justify-content:space-between;align-items:center;font-family:Mono,Sans;font-size:21px;
  letter-spacing:.12em;font-weight:600;position:relative;z-index:2}
.foot i{display:inline-block;width:12px;height:12px;border-radius:50%%;background:var(--dot);margin-right:12px;vertical-align:1px}
.foot .site{font-weight:400}
.layer{position:absolute;inset:0;overflow:hidden;pointer-events:none;z-index:0}
.tex{position:absolute}
.bars div{height:14px;border-radius:2px;margin-top:12px}
"""


def head(theme, tag):
    logo = 'brand/steplan-logo-horizontal-reverse.svg' if theme == 'dark' else 'brand/steplan-logo-horizontal.svg'
    tag_html = f'<span class="tag">{esc(tag)}</span>' if tag else ''
    return f'<header class="head"><img class="logo" src="{uri(logo)}">{tag_html}</header>'


def tex(rel, cls=''):
    """装饰插图放在单独裁切的图层里：伸出画布的部分不算作内容溢出。"""
    return f'<div class="layer"><img class="tex {cls}" src="{uri(rel)}"></div>'


def foot(site='steplan.ai'):
    return f'<footer class="foot"><span><i></i>STEPLAN 阶梯计划</span><span class="site">{esc(site)}</span></footer>'


def bars(theme, width='46%'):
    c = {'dark': (BONE, BONE, LIME), 'lime': (VOID, VOID, VOID), 'bone': (VOID, VOID, LIME)}[theme]
    return (f'<div class="bars" style="width:{width}">' + ''.join(
        f'<div style="width:{w};background:{col}"></div>' for w, col in zip(('30%', '58%', '100%'), c)) + '</div>')


# ── 模板：训练营 / 活动招生 ───────────────────────────────────────
CAMP_CSS = """
#poster{padding:64px 72px 52px}
.c-tex{right:-60px;top:130px;width:760px;opacity:.55}
.hero{flex:none;margin-top:var(--gap-hero);position:relative;z-index:1}
.kicker{font-family:Mono,Sans;font-size:26px;letter-spacing:.12em;color:var(--acc);font-weight:600;margin-bottom:26px}
.headline{font-family:Display;font-size:150px;line-height:1.1}
.sub{font-size:34px;line-height:1.55;color:var(--dim);margin-top:30px;max-width:900px}
.stages{flex:1 0 var(--min-grow);display:flex;align-items:flex-end;gap:18px;margin-top:52px;position:relative;z-index:1}
.stage{flex:1;border-radius:20px;background:var(--card);color:var(--cardfg);padding:26px 24px;display:flex;flex-direction:column}
.stage:nth-child(1){height:60%}.stage:nth-child(2){height:80%}.stage:nth-child(3){height:100%}
.stage .no{font-family:Mono,Sans;font-size:19px;letter-spacing:.12em;opacity:.7}
.stage .tt{font-family:Display;font-size:46px;margin-top:10px;line-height:1.15}
.stage .ds{font-size:22px;line-height:1.5;opacity:.75;margin-top:12px}
.stage.peak{background:var(--peak);color:var(--peakfg)}
.points{flex:1 0 auto;display:flex;flex-direction:column;justify-content:flex-end;margin-top:52px}
.point{display:flex;align-items:baseline;gap:28px;padding:24px 0;border-top:2px solid var(--line)}
.point .no{font-family:Mono;font-size:24px;color:var(--acc);font-weight:700}
.point .tx{font-family:Display;font-size:44px;line-height:1.3}
.info{flex:none;display:flex;margin-top:26px;border-radius:20px;background:var(--card);color:var(--cardfg)}
.cell{flex:1;padding:24px 28px}
.cell+.cell{border-left:2px solid rgba(138,141,148,.25)}
.cell .lb{font-family:Mono,Sans;font-size:19px;letter-spacing:.12em;opacity:.6}
.cell{min-width:0}
.cell .vl{font-family:Display;font-size:48px;margin-top:6px;color:var(--peak);white-space:nowrap}
.t-lime .cell .vl{color:#C8FF2E}
.cta{flex:none;margin-top:18px;margin-bottom:40px;border-radius:20px;background:var(--peak);color:var(--peakfg);padding:30px 34px;
  display:flex;justify-content:space-between;align-items:center;gap:24px}
.cta .how{font-family:Display;font-size:50px;line-height:1.2}
.cta .how .hl{background:var(--peakfg);color:var(--peak)}
.cta .note{font-family:Mono,Sans;font-size:22px;letter-spacing:.1em;margin-top:12px;font-weight:600}
.cqr{width:190px;height:190px;background:#fff;padding:12px;border-radius:14px;flex:none}
.cqr img,.cqr svg{width:100%;height:100%;display:block}
.s-34 .stage .ds{display:none}
.s-34 .stage{padding:20px 22px}.s-34 .stage .tt{font-size:40px}
.s-34 .stage:nth-child(1){height:72%}.s-34 .stage:nth-child(2){height:86%}
.s-34 .point{padding:16px 0}.s-34 .point .tx{font-size:38px}
"""


def camp(spec, size, theme):
    need(spec, 'headline')
    t = theme
    parts = [tex('brand/texture-tall.png', 'c-tex') if t == 'dark' else '',
             head(t, spec.get('tag', '招募中')),
             '<section class="hero">'
             + (f'<p class="kicker">{esc(spec["kicker"])}</p>' if spec.get('kicker') else '')
             + f'<h1 class="headline" data-fit="84">{rich(spec["headline"])}</h1>'
             + (f'<p class="sub" data-fit="24">{rich(spec["sub"])}</p>' if spec.get('sub') else '') + '</section>']
    if spec.get('stages'):
        cards = ''
        for k, st in enumerate(spec['stages'][:3]):
            peak = ' peak' if k == len(spec['stages'][:3]) - 1 else ''
            cards += (f'<div class="stage{peak}"><p class="no">{esc(st.get("no", f"第 {k + 1} 阶"))}</p>'
                      f'<p class="tt">{rich(st["title"])}</p>'
                      + (f'<p class="ds">{rich(st["desc"])}</p>' if st.get('desc') else '') + '</div>')
        parts.append(f'<section class="stages">{cards}</section>')
    elif spec.get('points'):
        parts.append('<section class="points">' + ''.join(
            f'<div class="point"><span class="no">{k + 1:02d}</span><span class="tx">{rich(p)}</span></div>'
            for k, p in enumerate(spec['points'])) + '</section>')
    else:
        parts.append('<div style="flex:1;min-height:40px"></div>')
    if spec.get('info'):
        parts.append('<section class="info">' + ''.join(
            f'<div class="cell"><p class="lb">{esc(k)}</p><p class="vl" data-fit="26">{esc(v)}</p></div>' for k, v in spec['info'])
            + '</section>')
    cta = spec.get('cta') or {}
    if cta:
        qr = qr_html(cta, 'cqr') if (cta.get('qr') or cta.get('qr_url')) else ''
        parts.append(f'<section class="cta"><div><p class="how" data-fit="32">{rich(cta["how"])}</p>'
                     + (f'<p class="note">{esc(cta["note"])}</p>' if cta.get('note') else '') + f'</div>{qr}</section>')
    parts.append(foot(spec.get('site', 'steplan.ai')))
    gap = {'9:16': ('96px', '240px'), '3:4': ('48px', '190px')}[size]
    return ''.join(parts), CAMP_CSS, f'--gap-hero:{gap[0]};--min-grow:{gap[1]}'


# ── 模板：课程海报（长图 / 9:16 单屏） ────────────────────────────
COURSE_CSS = """
.qr{background:#fff;border-radius:18px;padding:16px;flex:none}
.qr img,.qr svg{width:100%;height:100%;display:block}
.qr-ph{display:flex;align-items:center;justify-content:center;text-align:center;border:3px dashed #8A8D94;
  font-family:Mono,Sans;font-size:20px;letter-spacing:.12em;color:#8A8D94;line-height:1.6}
.ph-ph{display:flex;align-items:center;justify-content:center;background:#2A2C33;color:#C8FF2E;font-family:Display}
.sec{position:relative;padding:76px 72px;background:var(--bg);color:var(--fg)}
.sec-k{font-family:Mono,Sans;font-size:24px;letter-spacing:.14em;color:var(--muted);font-weight:600}
.sec-t{font-family:Display;font-size:66px;line-height:1.2;margin-top:8px}
.sec-bar{width:56px;height:8px;background:var(--acc);margin-top:22px;border-radius:2px}
.kicker{font-family:Mono,Sans;font-size:26px;letter-spacing:.12em;color:var(--acc);font-weight:600;margin-bottom:26px}
.headline{font-family:Display;font-size:150px;line-height:1.1;position:relative;z-index:1}
.sub{font-size:34px;line-height:1.55;color:var(--dim);margin-top:30px;position:relative;z-index:1}
.c-tex{right:-60px;top:110px;width:760px;opacity:.5}
.chip{display:inline-block;border:2px solid var(--line);border-radius:30px;padding:8px 18px;font-size:22px;
  margin:0 10px 10px 0;line-height:1.3}
/* 长图 */
.hero{padding-top:64px;padding-bottom:84px}
.hero .headline{margin-top:0}
.hero-body{margin-top:110px}
.igrid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:60px;position:relative;z-index:1}
.ig{background:var(--card);border-radius:18px;padding:24px 28px}
.ig .lb{font-family:Mono,Sans;font-size:20px;letter-spacing:.12em;color:var(--muted)}
.ig .vl{font-family:Display;font-size:40px;margin-top:8px;color:var(--peak)}
.gain{display:grid;grid-template-columns:96px 1fr;align-items:baseline;padding:28px 0;border-top:2px solid var(--line)}
.gain:first-of-type{margin-top:36px}
.gain .no{font-family:Wide;font-weight:600;font-size:40px;color:var(--acc)}
.gain .tx{font-size:34px;line-height:1.5}
.sc{border-radius:22px;background:var(--card);color:var(--cardfg);padding:34px 38px 20px;margin-top:22px}
.sc:first-of-type{margin-top:40px}
.sc.peak{background:#16171C;color:#F4F5F0}
.sc-top{display:flex;justify-content:space-between;align-items:center}
.sc-no{font-family:Mono,Sans;font-size:22px;letter-spacing:.12em;font-weight:700}
.sc.peak .sc-no{color:#C8FF2E}
.st{display:flex;flex-direction:column;align-items:flex-end;gap:5px}
.st i{display:block;height:7px;border-radius:2px;background:#DCDDD6}
.st i.on{background:#16171C}
.sc.peak .st i{background:#3A3C44}.sc.peak .st i.on{background:#C8FF2E}
.sc-title{font-family:Display;font-size:54px;margin:14px 0 16px}
.lesson{display:grid;grid-template-columns:78px 1fr;padding:16px 0;border-top:2px dashed var(--line);font-size:30px;line-height:1.45}
.sc.peak .lesson{border-top-color:#2E3038}
.lesson .ln{font-family:Mono;font-size:22px;color:var(--muted);padding-top:6px}
.teacher{display:grid;grid-template-columns:230px 1fr;gap:44px;margin-top:48px;align-items:start}
.photo{width:230px;height:230px;border-radius:50%;object-fit:cover;font-size:96px}
.tname{font-family:Display;font-size:62px;line-height:1.15}
.ttitle{font-family:Mono,Sans;font-size:22px;letter-spacing:.1em;color:var(--acc);font-weight:600;margin-top:10px}
.tbio{font-size:30px;line-height:1.6;color:var(--dim);margin-top:20px}
.ttags{margin-top:22px}
.aud{display:flex;align-items:center;gap:22px;padding:22px 0;border-top:2px solid var(--line);font-size:32px}
.aud:first-of-type{margin-top:36px}
.aud .ck{width:44px;height:44px;border-radius:10px;background:#16171C;color:#C8FF2E;display:flex;align-items:center;
  justify-content:center;font-size:26px;font-weight:700;flex:none}
.price{margin-top:44px;background:#16171C;color:#F4F5F0;border-radius:22px;padding:40px 44px;display:flex;
  justify-content:space-between;align-items:flex-end;gap:24px}
.price .lb{font-family:Mono,Sans;font-size:22px;letter-spacing:.14em;color:#8A8D94}
.price .now{font-family:Display;font-size:104px;line-height:1;color:#C8FF2E;margin-top:12px}
.price .orig{font-size:26px;color:#8A8D94;text-decoration:line-through;margin-top:10px}
.price .note{font-size:24px;color:#B4B6AF;text-align:right;max-width:360px;line-height:1.5}
.signup{display:flex;gap:48px;align-items:center;margin-top:44px}
.signup .qr{width:340px;height:340px}
.su-t{font-family:Display;font-size:84px;line-height:1.1}
.su-n{font-size:32px;line-height:1.5;margin-top:18px}
.su-d{display:inline-block;margin-top:26px;background:#16171C;color:#C8FF2E;font-size:28px;font-weight:700;
  padding:12px 22px;border-radius:12px}
.s-long .foot{margin-top:72px}
/* 9:16 单屏 */
.s-916{padding:64px 72px 52px}
.s-916 .hero-body{margin-top:60px}
.s-916 .headline{font-size:124px}
.s-916 .sub{font-size:30px;margin-top:22px}
.s-916 .chips{margin-top:30px;position:relative;z-index:1}
.s-916 .chip{font-size:21px;border-color:#3A3C44}
.s-916 .chip b{color:#C8FF2E;margin-left:8px}
.blk-k{font-family:Mono,Sans;font-size:21px;letter-spacing:.14em;color:#8A8D94;font-weight:600;margin:38px 0 16px}
.cols{display:flex;gap:14px;align-items:stretch}
.col{flex:1;background:#1F2027;border-radius:18px;padding:22px 22px 18px;min-width:0}
.col.peak{background:#C8FF2E;color:#16171C}
.col .cn{font-family:Mono,Sans;font-size:18px;letter-spacing:.1em;opacity:.7}
.col .ct{font-family:Display;font-size:40px;margin:8px 0 10px}
.col .cl{font-size:21px;line-height:1.45;padding:7px 0;border-top:1.5px solid rgba(138,141,148,.3)}
.trow{display:flex;gap:28px;align-items:center}
.trow .photo{width:128px;height:128px;font-size:56px}
.trow .tname{font-size:46px}
.trow .ttitle{font-size:19px;margin-top:6px}
.trow .tbio{font-size:22px;margin-top:10px;line-height:1.5}
.sbox{flex:none;margin-top:auto;background:#C8FF2E;color:#16171C;border-radius:22px;padding:28px;display:flex;gap:32px;align-items:center}
.sbox .qr{width:236px;height:236px;padding:12px}
.sbox .su-t{font-size:62px}
.sbox .su-n{font-size:24px;margin-top:10px}
.sbox .su-d{font-size:22px;margin-top:16px;padding:9px 16px}
.sbox .pr{font-family:Display;font-size:34px;margin-top:14px}
.s-916 .foot{margin-top:36px}
"""


def stair_html(n):
    return '<span class="st">' + ''.join(
        f'<i class="{"on" if 3 - k <= n else ""}" style="width:{18 * (k + 1)}px"></i>' for k in range(3)) + '</span>'


def course(spec, size, theme):
    need(spec, 'headline', 'outline')
    signup = spec.get('signup') or {}
    outline = spec['outline']
    teachers = spec.get('teachers', [])
    kicker = f'<p class="kicker">{esc(spec["kicker"])}</p>' if spec.get('kicker') else ''
    sub = f'<p class="sub" data-fit="22">{rich(spec["sub"])}</p>' if spec.get('sub') else ''
    texture = tex('brand/texture-tall.png', 'c-tex')
    if size == 'long':
        h = (f'<section class="sec hero t-dark">{texture}{head("dark", spec.get("tag", "招募中"))}'
             f'<div class="hero-body">{kicker}<h1 class="headline">{rich(spec["headline"])}</h1>{sub}</div>'
             + ('<div class="igrid">' + ''.join(f'<div class="ig"><p class="lb">{esc(k)}</p><p class="vl">{esc(v)}</p></div>'
                                                for k, v in spec.get('info', [])) + '</div>' if spec.get('info') else '')
             + '</section>')

        def heading(k, t):
            return f'<p class="sec-k">{esc(k)}</p><h2 class="sec-t">{esc(t)}</h2><div class="sec-bar"></div>'
        if spec.get('gains'):
            h += (f'<section class="sec t-bone">{heading("WHAT YOU GET · 你将收获", spec.get("gains_title", "学完你会带走"))}'
                  + ''.join(f'<div class="gain"><span class="no">{k + 1:02d}</span><span class="tx">{rich(g)}</span></div>'
                            for k, g in enumerate(spec['gains'])) + '</section>')
        cards = ''
        for k, st in enumerate(outline):
            peak = ' peak' if k == len(outline) - 1 else ''
            lessons = ''.join(f'<div class="lesson"><span class="ln">{k + 1}.{j + 1}</span><span>{rich(ls)}</span></div>'
                              for j, ls in enumerate(st.get('lessons', [])))
            cards += (f'<div class="sc{peak}"><div class="sc-top"><span class="sc-no">{esc(st.get("stage", f"第 {k + 1} 阶"))}'
                      f'{"  ·  " + esc(st["week"]) if st.get("week") else ""}</span>{stair_html(min(k + 1, 3))}</div>'
                      f'<p class="sc-title">{rich(st["title"])}</p>{lessons}</div>')
        h += f'<section class="sec t-bone" style="padding-top:20px">{heading("CURRICULUM · 课程大纲", spec.get("outline_title", "课程大纲"))}{cards}</section>'
        if teachers:
            h += (f'<section class="sec t-dark">{heading("TEACHER · 讲师", spec.get("teacher_title", "讲师介绍"))}'
                  + ''.join(f'<div class="teacher">{photo_html(t)}<div><p class="tname">{esc(t["name"])}</p>'
                            + (f'<p class="ttitle">{esc(t["title"])}</p>' if t.get('title') else '')
                            + (f'<p class="tbio">{rich(t["bio"])}</p>' if t.get('bio') else '')
                            + ('<div class="ttags">' + ''.join(f'<span class="chip">{esc(x)}</span>' for x in t['tags'])
                               + '</div>' if t.get('tags') else '') + '</div></div>' for t in teachers) + '</section>')
        if spec.get('audience') or spec.get('price'):
            pr = spec.get('price') or {}
            h += (f'<section class="sec t-bone">{heading("WHO IS IT FOR · 适合谁", spec.get("audience_title", "适合谁"))}'
                  + ''.join(f'<div class="aud"><span class="ck">✓</span><span>{rich(a)}</span></div>'
                            for a in spec.get('audience', []))
                  + (f'<div class="price"><div><p class="lb">{esc(pr.get("label", "早鸟价"))}</p>'
                     f'<p class="now">{esc(pr["now"])}</p>'
                     + (f'<p class="orig">{esc(pr["orig"])}</p>' if pr.get('orig') else '') + '</div>'
                     + (f'<p class="note">{esc(pr["note"])}</p>' if pr.get('note') else '') + '</div>' if pr.get('now') else '')
                  + '</section>')
        h += (f'<section class="sec t-lime">{heading("SIGN UP · 报名", spec.get("signup_heading", "报名方式"))}'
              f'<div class="signup">{qr_html(signup)}<div><p class="su-t">{rich(signup.get("title", "扫码报名"))}</p>'
              + (f'<p class="su-n">{rich(signup["note"])}</p>' if signup.get('note') else '')
              + (f'<span class="su-d">{esc(signup["deadline"])}</span>' if signup.get('deadline') else '')
              + f'</div></div>{foot(spec.get("site", "steplan.ai"))}</section>')
        return h, COURSE_CSS, 'display:block;padding:0'

    # 9:16 单屏：精简大纲 + 讲师 + 报名
    chips = ''.join(f'<span class="chip">{esc(k)}<b>{esc(v)}</b></span>' for k, v in spec.get('info', []))
    cols = ''.join(
        f'<div class="col{" peak" if k == len(outline) - 1 else ""}"><p class="cn">{esc(st.get("stage", f"第 {k + 1} 阶"))}'
        f'{" · " + esc(st["week"]) if st.get("week") else ""}</p><p class="ct">{rich(st["title"])}</p>'
        + ''.join(f'<p class="cl">{rich(ls)}</p>' for ls in st.get('lessons', [])[:3]) + '</div>'
        for k, st in enumerate(outline[:3]))
    t = teachers[0] if teachers else None
    trow = (f'<p class="blk-k">TEACHER · 讲师</p><div class="trow">{photo_html(t)}<div><p class="tname">{esc(t["name"])}</p>'
            + (f'<p class="ttitle">{esc(t["title"])}</p>' if t.get('title') else '')
            + (f'<p class="tbio" data-fit="18">{rich(t["bio"])}</p>' if t.get('bio') else '') + '</div></div>') if t else ''
    pr = spec.get('price') or {}
    sbox = (f'<div class="sbox">{qr_html(signup)}<div><p class="su-t">{rich(signup.get("title", "扫码报名"))}</p>'
            + (f'<p class="su-n">{rich(signup["note"])}</p>' if signup.get('note') else '')
            + (f'<p class="pr">{esc(pr.get("label", "早鸟价"))} {esc(pr["now"])}</p>' if pr.get('now') else '')
            + (f'<span class="su-d">{esc(signup["deadline"])}</span>' if signup.get('deadline') else '') + '</div></div>')
    body = (texture + head('dark', spec.get('tag', '招募中'))
            + f'<div class="hero-body">{kicker}<h1 class="headline" data-fit="72">{rich(spec["headline"])}</h1>{sub}</div>'
            + (f'<div class="chips">{chips}</div>' if chips else '')
            + f'<p class="blk-k">CURRICULUM · 课程大纲</p><div class="cols">{cols}</div>'
            + trow + '<div style="flex:1;min-height:36px"></div>' + sbox + foot(spec.get('site', 'steplan.ai')))
    return body, COURSE_CSS, ''


# ── 模板：产品推广 ────────────────────────────────────────────────
PRODUCT_CSS = """
#poster{padding:64px 72px 52px}
.pname{font-family:Wide;font-weight:600;font-size:150px;letter-spacing:-.03em;line-height:1;margin-top:var(--gap-hero);
  transform:skewX(-8deg);transform-origin:left bottom;white-space:nowrap}
.tagline{font-family:Display;font-size:76px;line-height:1.2;margin-top:30px}
.subrow{display:flex;align-items:center;gap:20px;margin-top:22px;flex-wrap:wrap}
.subrow .sub{font-size:32px;line-height:1.5;color:var(--dim)}
.badge{background:#C8FF2E;color:#16171C;font-weight:700;font-size:28px;line-height:1;padding:12px 22px;border-radius:12px}
.t-lime .badge{background:#16171C;color:#C8FF2E}
.visual{flex:1 0 var(--min-grow);margin-top:46px;border-radius:24px;overflow:hidden;position:relative;background:#16171C}
.t-dark .visual{background:#1F2027}
.visual .shot{width:100%;height:100%;object-fit:cover;object-position:top;display:block}
.visual .vtex{position:absolute;right:-60px;top:-40px;width:115%}
.visual .vlab{position:absolute;left:30px;bottom:26px;font-family:Mono,Sans;font-size:20px;letter-spacing:.14em;color:#B4B6AF;background:rgba(22,23,28,.88);padding:10px 16px;border-radius:8px}
.feats{flex:none;margin-top:30px}
.feat{display:grid;grid-template-columns:84px 1fr;padding:22px 0;border-top:2px solid var(--line)}
.feat .no{font-family:Mono;font-size:22px;color:var(--muted);font-weight:700;padding-top:10px}
.feat .tt{font-family:Display;font-size:42px;line-height:1.25}
.feat .ds{font-size:24px;line-height:1.5;color:var(--dim);margin-top:6px}
.url{flex:none;margin-top:26px;margin-bottom:40px;background:#16171C;color:#F4F5F0;border-radius:20px;padding:28px 34px;
  display:flex;justify-content:space-between;align-items:center;gap:20px}
.t-dark .url{background:#C8FF2E;color:#16171C}
.url .u{font-family:Mono;font-size:40px;letter-spacing:.04em;font-weight:700;color:#C8FF2E;white-space:nowrap}
.t-dark .url .u{color:#16171C}
.url .c{font-size:26px;line-height:1.4;opacity:.8;text-align:right}
.s-34 .feat .ds{display:none}
.s-34 .feat{padding:14px 0}.s-34 .feat .no{padding-top:6px}.s-34 .tagline{font-size:64px}
"""


def product(spec, size, theme):
    need(spec, 'name', 'tagline')
    if spec.get('image'):
        vis = f'<img class="shot" src="{local(spec["image"])}">'
    else:
        vis = (f'<img class="vtex" src="{uri("brand/texture-wide.png")}">'
               f'<span class="vlab">{esc(spec.get("visual_label", "SCREENSHOT · 产品截图位"))}</span>')
    feats = ''.join(
        f'<div class="feat"><span class="no">{k + 1:02d}</span><div><p class="tt">{rich(f[0])}</p>'
        + (f'<p class="ds">{rich(f[1])}</p>' if len(f) > 1 and f[1] else '') + '</div></div>'
        for k, f in enumerate(spec.get('features', [])[:3]))
    sub = (f'<span class="sub">{rich(spec["sub"])}</span>' if spec.get('sub') else '') + (
        f'<span class="badge">{esc(spec["badge"])}</span>' if spec.get('badge') else '')
    body = (head(theme, spec.get('tag', 'NEW · 已上线'))
            + f'<h1 class="pname" data-fit="80">{esc(spec["name"])}</h1>'
            + f'<p class="tagline" data-fit="48">{rich(spec["tagline"])}</p>'
            + (f'<div class="subrow">{sub}</div>' if sub else '')
            + f'<section class="visual">{vis}</section>'
            + (f'<section class="feats">{feats}</section>' if feats else '')
            + (f'<section class="url"><span class="u">→ {esc(spec["url"])}</span>'
               + (f'<span class="c">{rich(spec["cta"])}</span>' if spec.get('cta') else '') + '</section>'
               if spec.get('url') else '<div style="height:40px"></div>')
            + foot(spec.get('site', 'steplan.ai')))
    gap = {'9:16': ('96px', '300px'), '3:4': ('48px', '250px')}[size]
    return body, PRODUCT_CSS, f'--gap-hero:{gap[0]};--min-grow:{gap[1]}'


# ── 模板：金句 / 观点 ────────────────────────────────────────────
QUOTE_CSS = """
#poster{padding:72px 72px 52px}
.qhead{flex:none;display:flex;justify-content:space-between;align-items:flex-start}
.qtag{font-family:Mono,Sans;font-size:24px;letter-spacing:.16em;font-weight:700;padding-top:10px}
.bigdot{width:150px;height:150px;border-radius:50%;background:var(--dot);flex:none}
.qbody{flex:1;display:flex;flex-direction:column;justify-content:center;min-height:0}
.num{font-family:Wide;font-weight:600;font-size:250px;line-height:.95;letter-spacing:-.05em;color:var(--acc);white-space:nowrap}
.num small{font-size:.36em;letter-spacing:0;margin-left:.1em}
.numlabel{font-size:32px;line-height:1.5;color:var(--dim);margin:22px 0 70px;max-width:860px}
.qtext{font-family:Display;font-size:128px;line-height:1.2}
.src{font-family:Mono,Sans;font-size:26px;letter-spacing:.1em;margin-top:44px;color:var(--muted)}
.qfoot{flex:none}
.qfoot .bars{margin-bottom:44px}
"""


def quote(spec, size, theme):
    need(spec, 'text')
    num = spec.get('number') or {}
    num_html = ''
    if num:
        unit = f'<small>{esc(num["unit"])}</small>' if num.get('unit') else ''
        num_html = (f'<p class="num" data-fit="120">{esc(num["value"])}{unit}</p>'
                    + (f'<p class="numlabel">{rich(num["label"])}</p>' if num.get('label') else ''))
    body = (f'<header class="qhead"><span class="qtag">{esc(spec.get("tag", "KEY POINT · 观点"))}</span>'
            f'<span class="bigdot"></span></header>'
            f'<section class="qbody">{num_html}<p class="qtext" data-fit="64">{rich(spec["text"])}</p>'
            + (f'<p class="src">{esc(spec["source"])}</p>' if spec.get('source') else '') + '</section>'
            f'<div class="qfoot">{bars(theme)}{foot(spec.get("site", "steplan.ai"))}</div>')
    return body, QUOTE_CSS, ''


# ── 模板：封面图（公众号主图 + 次图 + 小红书） ─────────────────────
COVER_CSS = {
    '公众号封面': """
#poster{flex-direction:row}
.cl{flex:0 0 62%;padding:34px 40px 30px;display:flex;flex-direction:column;position:relative;z-index:1}
.cr{flex:1;position:relative;overflow:hidden;background:var(--art)}
.cr img{position:absolute;right:-30px;top:-20px;width:150%}
.cr::before{content:'';position:absolute;inset:0;z-index:1;background:linear-gradient(90deg,var(--bg) 0%,transparent 35%)}
.series{font-family:Mono,Sans;font-size:15px;letter-spacing:.14em;color:var(--muted);font-weight:600}
.ctitle{font-family:Display;font-size:60px;line-height:1.14;margin-top:auto;margin-bottom:auto}
.foot{font-size:13px}.foot i{width:8px;height:8px;margin-right:8px}
.t-dark{--art:#16171C}.t-lime{--art:#16171C}.t-bone{--art:#16171C}
""",
    '公众号次图': """
#poster{padding:38px 38px 32px}
.series{font-family:Mono,Sans;font-size:14px;letter-spacing:.14em;color:var(--muted);font-weight:600}
.ctitle{font-family:Display;font-size:62px;line-height:1.15;margin-top:auto;margin-bottom:auto;position:relative;z-index:1}
.tex{right:-90px;bottom:-60px;width:360px;opacity:.5}
.foot{font-size:12px}.foot i{width:8px;height:8px;margin-right:8px}
.bars{margin-bottom:22px}.bars div{height:8px;margin-top:7px}
""",
    '小红书封面': """
#poster{padding:72px 72px 52px}
.series{font-family:Mono,Sans;font-size:26px;letter-spacing:.14em;color:var(--muted);font-weight:600;margin-top:70px}
.ctitle{font-family:Display;font-size:150px;line-height:1.14;margin-top:34px;position:relative;z-index:1}
.csub{font-size:40px;line-height:1.5;color:var(--dim);margin-top:40px;position:relative;z-index:1}
.tex{right:-160px;bottom:-120px;width:820px;opacity:.6}
.bars{margin-top:auto;margin-bottom:44px}
""",
}


def cover(spec, label, theme):
    need(spec, 'title')
    series = f'<p class="series">{esc(spec["series"])}</p>' if spec.get('series') else ''
    art = 'texture-wide.png' if label == '公众号封面' else 'texture-tall.png'
    if label == '公众号封面':
        body = (f'<div class="cl">{series}<h1 class="ctitle" data-fit="34">{rich(spec["title"])}</h1>{foot("")}</div>'
                f'<div class="cr"><img src="{uri("brand/" + art)}"></div>')
    elif label == '公众号次图':
        body = (f'{tex("brand/" + art)}{series}'
                f'<h1 class="ctitle" data-fit="34">{rich(spec.get("title_square") or spec["title"])}</h1>'
                f'{bars(theme, "40%")}{foot("")}')
    else:
        body = (tex('brand/' + art) + head(theme, spec.get('tag', '')) + series
                + f'<h1 class="ctitle" data-fit="80">{rich(spec["title"])}</h1>'
                + (f'<p class="csub" data-fit="28">{rich(spec["sub"])}</p>' if spec.get('sub') else '')
                + bars(theme) + foot(spec.get('site', 'steplan.ai')))
    return body, COVER_CSS[label], ''


TEMPLATES = {
    'course': (course, 'dark', '课程海报：headline、outline 必填；tag、kicker、sub、info、gains、outline[{stage,week,title,lessons}]、'
                               'teachers[{name,title,bio,tags,photo}]、audience、price{label,now,orig,note}、'
                               'signup{qr | qr_url,title,note,deadline}；sizes 默认 long + 9:16'),
    'camp': (camp, 'dark', '训练营 / 活动招生：headline 必填；kicker、sub、stages(≤3) 或 points、info、cta{how,note,qr}'),
    'product': (product, 'bone', '产品推广：name、tagline 必填；sub、badge、image、features(≤3)、url、cta'),
    'quote': (quote, 'lime', '金句 / 观点：text 必填；tag、source、number{value,unit,label}'),
    'cover': (cover, 'dark', '封面图：title 必填；series、title_square（次图用的短标题）、sub（小红书用）、tag'),
}

FIT_JS = """
() => {
  const P = document.getElementById('poster');
  const boxes = [...P.querySelectorAll('.stage,.cta,.info,.cell,.url,.feat,.point,.qbody,.cl')];
  const over = () => P.scrollHeight > P.clientHeight + 1 || boxes.some(b => b.scrollHeight > b.clientHeight + 2);
  const fits = [...document.querySelectorAll('[data-fit]')];
  const size = el => parseFloat(getComputedStyle(el).fontSize);
  for (const el of fits) {            // 先处理横向溢出（单词过长）
    while (el.scrollWidth > el.clientWidth + 1 && size(el) > +el.dataset.fit) el.style.fontSize = (size(el) - 2) + 'px';
  }
  for (let guard = 0; over() && guard < 800; guard++) {   // 每次缩当前最大的那段字，保持层级
    const el = fits.filter(e => size(e) > +e.dataset.fit).sort((a, b) => size(b) - size(a))[0];
    if (!el) break;
    el.style.fontSize = (size(el) - 2) + 'px';
  }
  const warns = [];
  if (over()) warns.push('内容放不下：请缩短文字或去掉可选块');
  for (const el of fits) {
    if (size(el) <= +el.dataset.fit + 0.5) warns.push(`「${el.innerText.slice(0, 12)}…」已缩到最小字号 ${el.dataset.fit}px，建议缩短`);
    if (el.scrollWidth > el.clientWidth + 1) warns.push(`「${el.innerText.slice(0, 12)}…」横向放不下`);
  }
  return warns;
}
"""


def page_html(body, css, theme, size_cls, w, h, style):
    return (f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><style>'
            f'{CSS % {"f": (ASSETS / "fonts").resolve().as_uri()}}{css}</style></head><body>'
            f'<div id="poster" class="t-{theme} {size_cls}" style="width:{w}px;{f"height:{h}px;" if h else ""}{style}">{body}</div>'
            f'</body></html>')


def jobs_for(spec, src):
    tpl = spec.get('template')
    if tpl not in TEMPLATES:
        sys.exit(f'{src}：template 必须是 {" / ".join(TEMPLATES)}，现在是 {tpl!r}')
    fn, default_theme, _ = TEMPLATES[tpl]
    theme = spec.get('theme', default_theme)
    if theme not in ('dark', 'lime', 'bone'):
        sys.exit(f'{src}：theme 必须是 dark / lime / bone')
    out = []
    try:
        if tpl == 'cover':
            for label, (w, h) in COVER_SIZES.items():
                body, css, style = fn(spec, label, theme)
                out.append((label, w, h, page_html(body, css, theme, '', w, h, style)))
        else:
            default = ['long', '9:16'] if tpl == 'course' else ['9:16', '3:4']
            for size in spec.get('sizes', default):
                if size not in POSTER_SIZES:
                    sys.exit(f'{src}：sizes 只能是 {" / ".join(POSTER_SIZES)}')
                w, h = POSTER_SIZES[size]
                body, css, style = fn(spec, size, theme)
                out.append(({'long': '长图'}.get(size, size.replace(':', 'x')), w, h,
                            page_html(body, css, theme, 's-' + size.replace(':', ''), w, h, style)))
    except (KeyError, ValueError, TypeError, IndexError) as e:
        sys.exit(f'{src}（{tpl}）字段有误：{e}\n{TEMPLATES[tpl][2]}')
    return out


def render(paths, out_dir, scale_mul):
    from playwright.sync_api import sync_playwright
    out_dir.mkdir(parents=True, exist_ok=True)
    made, problems = [], 0
    with sync_playwright() as p, tempfile.TemporaryDirectory() as tmp:
        try:
            browser = p.chromium.launch(channel='chrome')
        except Exception:
            browser = p.chromium.launch()
        for path in paths:
            try:
                spec = json.loads(path.read_text(encoding='utf-8'))
            except json.JSONDecodeError as e:
                sys.exit(f'{path}：JSON 格式错误：{e}')
            for label, w, h, doc in jobs_for(spec, path.name):
                f = pathlib.Path(tmp) / f'{path.stem}-{label}.html'
                f.write_text(doc, encoding='utf-8')
                pg = browser.new_page(viewport={'width': w, 'height': h or 1920}, device_scale_factor=scale_mul)
                pg.goto(f.as_uri())
                pg.evaluate('document.fonts.ready.then(() => true)')
                pg.wait_for_load_state('networkidle')
                warns = pg.evaluate(FIT_JS)
                png = out_dir / f'{path.stem}-{label}.png'
                pg.locator('#poster').screenshot(path=str(png))
                pg.close()
                made.append(png)
                print(('⚠ ' if warns else '✓ ') + str(png) + ''.join(f'\n    ⚠ {x}' for x in warns))
                problems += bool(warns)
        browser.close()
    return made, problems


def main():
    ap = argparse.ArgumentParser(description='Steplan 阶梯计划 · 海报生成器')
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('render', help='poster.json → PNG')
    r.add_argument('specs', nargs='+', type=pathlib.Path)
    r.add_argument('-o', '--out', type=pathlib.Path, help='输出目录（默认：第一个 json 所在目录）')
    r.add_argument('--scale', type=int, default=2, help='输出倍率，默认 2（手机屏幕清晰）；3 更清晰、文件更大')
    sub.add_parser('fields', help='列出模板和字段')
    args = ap.parse_args()
    if args.cmd == 'fields':
        for k, (_, theme, doc) in TEMPLATES.items():
            print(f'{k}（默认主题 {theme}）— {doc}')
        print('主题 theme：dark / lime / bone；文字标记：[[反白色块]] ==酸性绿色块== **粗体** \\n 换行')
        return
    out = (args.out or args.specs[0].parent).resolve()
    made, problems = render(args.specs, out, args.scale)
    print(f'共 {len(made)} 张' + (f'，{problems} 张有提示需要处理' if problems else ''))


if __name__ == '__main__':
    main()

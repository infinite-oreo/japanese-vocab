#!/usr/bin/env python3
"""读取 data/*.md，生成 dist/index.html（可交互背诵版）。PDF 由 build.sh 调用 Chrome 打印该页面得到。"""
import re, html, glob, os

ROOT = os.path.dirname(os.path.abspath(__file__))

def rich(s):
    s = html.escape(s, quote=False).replace("&lt;br&gt;", "<br>")
    s = re.sub(r"\{([^|}]+)\|([^}]+)\}", r"<ruby>\1<rt>\2</rt></ruby>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return s.replace("[　]", '<span class="blank"></span>')

def split_title(s):
    a, _, b = s.partition("｜")
    return rich(a), rich(b)

def circ(n):
    return chr(0x2460 + n - 1) if n <= 20 else f"({n})"

def parse(path):
    lesson = {"part": "", "title": "", "progress": False, "key": os.path.splitext(os.path.basename(path))[0], "sections": []}
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        if line.startswith("progress:"):
            lesson["progress"] = line[9:].strip() == "on"
        elif line.startswith("part:"):
            lesson["part"] = line[5:].strip()
        elif line.startswith("### "):
            lesson["sections"][-1]["items"].append({"sub": line[4:].strip()})
        elif line.startswith("## "):
            lesson["sections"].append({"title": line[3:].strip(), "items": []})
        elif line.startswith("# "):
            lesson["title"] = line[2:].strip()
        elif line.startswith("- "):
            body, _, zh = line[2:].partition("=>")
            jp, _, choices = body.partition("●")
            lesson["sections"][-1]["items"].append(
                (jp.strip(), [c for c in choices.strip().split("／") if c] if choices.strip() else [], zh.strip()))
    return lesson

def render_zh(zh):
    out = []
    for pair in zh.split("；"):
        w, sep, m = pair.partition("：")
        out.append(f'<span class="w">{html.escape(w)}</span>{html.escape(m)}' if sep else html.escape(pair))
    return "<br>".join(out)

def main():
    lessons = [parse(p) for p in sorted(glob.glob(os.path.join(ROOT, "data", "*.md")))]
    toc, body, last_part = [], [], None
    for li, L in enumerate(lessons, 1):
        if L["part"] != last_part:
            pj, pz = split_title(L["part"])
            toc.append(f'<div class="toc-part">{pj}</div>')
            body.append(f'<h1 class="part">{pj}<small>{pz}</small></h1>')
            last_part = L["part"]
        tj, tz = split_title(L["title"])
        toc.append(f'<a class="toc-l" href="#l{li}">{tj}</a>')
        body.append(f'<h2 class="lesson" id="l{li}">{tj}<small>{tz}</small></h2>')
        for si, S in enumerate(L["sections"], 1):
            sid = f"l{li}s{si}"
            toc.append(f'<a class="toc-s" href="#{sid}">{si}. {rich(S["title"])}</a>')
            body.append(f'<h3 id="{sid}">{si}. {rich(S["title"])}</h3><ol class="entries">')
            n = 0
            idx = 0
            for item in S["items"]:
                if isinstance(item, dict):  # 小节内的小标题（教材中的 ● 分组）
                    body.append(f'</ol><h4 class="sub">{rich(item["sub"])}</h4><ol class="entries">')
                    continue
                jp, choices, zh = item
                idx += 1
                star = jp.startswith("★")
                if star:
                    jp = jp[1:].strip()
                else:
                    n += 1
                # 符号用法：／ 分隔意思不同但可替换的词；・ 连接近义词（同一标签内）
                chips = '<span class="sl">／</span>'.join(
                    '<span class="chip">' + '<span class="syn">・</span>'.join(rich(x) for x in c.split("・")) + '</span>'
                    for c in choices)
                lines, zhs = jp.split("<br>"), zh.split("；")
                if len(lines) > 1 and len(lines) == len(zhs):
                    # 多行条目：每行日语与对应释义放在同一行里，保证水平对齐
                    rows = "".join(
                        f'<div class="mrow"><div class="jp">{rich(l)}</div><div class="zh">{render_zh(z)}</div></div>'
                        for l, z in zip(lines, zhs))
                    main_html = f'<div class="multi">{rows}</div>'
                else:
                    main_html = (f'<div class="jp">{rich(jp)}<div class="chips">{chips}</div></div>'
                                 f'<div class="zh">{render_zh(zh)}</div>')
                body.append(
                    f'<li class="entry{" star" if star else ""}"><span class="no">{"★" if star else circ(n)}</span>'
                    + main_html
                    + (f'<div class="prog" data-key="{L["key"]}:{si}:{idx}"></div>' if L["progress"] else "")
                    + '</li>')
            body.append("</ol>")
    legend = ('<details class="legend" open><summary>符号用法</summary><ul>'
              '<li><span class="blank"></span><span>填入选项中的词语。</span></li>'
              '<li><span class="sym">A・B</span><span>A 和 B 为近义词。</span></li>'
              '<li><span class="sym">A／B</span><span>A 和 B 意思不同，但可替换使用。</span></li>'
              '<li><span class="sym">（　）</span><span>用其他形式表示（　）前的词语。</span></li></ul></details>')
    body.insert(0, legend)
    tpl = open(os.path.join(ROOT, "template.html"), encoding="utf-8").read()
    out = tpl.replace("{{TOC}}", "\n".join(toc)).replace("{{BODY}}", "\n".join(body))
    out = re.sub(r'<ol class="entries">\s*</ol>', "", out)  # 小节以小标题开头时产生的空列表
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    open(os.path.join(ROOT, "dist", "index.html"), "w", encoding="utf-8").write(out)
    print("已生成 dist/index.html")

main()

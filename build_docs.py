"""Render the Giftronaut integration BRD/PRD and PlantUML previews."""
from pathlib import Path
import argparse
import html
import re
import subprocess
import unicodedata
from urllib.parse import unquote

from markdown_it import MarkdownIt
from flow_layout import arrange, CSS, SCRIPT


ROOT = Path(__file__).resolve().parent
TITLE = "OP Points × ELLIS × Giftronaut — Integration BRD/PRD"


def slug(value):
    value = unicodedata.normalize("NFC", value.lower().strip())
    return re.sub(r"[^\w\- ]", "", value).replace(" ", "-")


def link_api_mentions(document, targets):
    """Turn visible API codes into local references, without nesting links/code."""
    protected = re.compile(r"(<(?:a|code|pre|h[1-6])\b[^>]*>.*?</(?:a|code|pre|h[1-6])>)", re.S)
    codes = "|".join(sorted(map(re.escape, targets), key=len, reverse=True))
    pattern = re.compile(rf"\b({codes})\b")

    def replace_text(fragment):
        return pattern.sub(lambda m: f'<a class="api-ref" href="#{targets[m.group(1)]}" title="Mở đặc tả {m.group(1)}">{m.group(1)}</a>', fragment)

    return "".join(
        part if protected.fullmatch(part) else replace_text(part)
        for part in protected.split(document)
    )


def build_html():
    source = ROOT / "OP-POINTS-ELLIS-GIFTRONAUT-INTEGRATION-BRD-PRD.md"
    markdown = MarkdownIt("commonmark", {"html": False}).enable("table")
    tokens = markdown.parse(source.read_text(encoding="utf-8"))
    headings, ids, api_targets = [], set(), {}
    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        title = tokens[index + 1].content
        anchor = slug(title)
        suffix = 2
        original = anchor
        while anchor in ids:
            anchor = f"{original}-{suffix}"
            suffix += 1
        ids.add(anchor)
        token.attrSet("id", anchor)
        code = re.match(r"((?:G|I)\d(?:[a-z-]+)?)\.", title)
        if code:
            api_targets[code.group(1)] = anchor
            if code.group(1) == "I7":
                api_targets["I7-resend"] = anchor
        if token.tag in ("h1", "h2") or (token.tag in ("h3", "h4") and re.match(r"[GF][0-8][ab]?\.", title)):
            headings.append((anchor, title, token.tag))

    document = markdown.renderer.render(tokens, markdown.options, {})
    document = arrange(document, api_targets)
    document = link_api_mentions(document, api_targets)
    ids.update(re.findall(r'\bid="([^"]+)"', document))
    for target in re.findall(r'(?:src|href)="([^"]+)"', document):
        if target.startswith("#"):
            if unquote(target[1:]) not in ids:
                raise ValueError(f"Missing document anchor: {target}")
        elif not re.match(r"[a-z]+:", target):
            if not (ROOT / html.unescape(target.split('#', 1)[0])).is_file():
                raise FileNotFoundError(target)

    nav = "".join(
        f'<a class="{tag}" href="#{anchor}">{html.escape(title)}</a>'
        for anchor, title, tag in headings
    )
    template = """<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title><style>
:root{color-scheme:light;--ink:#182B3A;--muted:#607080;--line:#D8E1E8;--brand:#006C70;--nav:#12343B;--soft:#EDF7F6}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#F2F5F6;color:var(--ink);font:16px/1.72 "Segoe UI",Arial,sans-serif}
aside{position:fixed;inset:0 auto 0 0;width:292px;padding:27px 22px;overflow:auto;background:var(--nav);color:white}aside strong{display:block;font-size:21px;line-height:1.3;margin-bottom:5px}aside small{display:block;color:#B9D3D2;margin-bottom:20px}
nav a{display:block;color:#D9E8E7;text-decoration:none;font-size:13px;line-height:1.4;padding:5px 0}nav a.h1{font-weight:700;margin-top:10px;color:white}nav a:hover{text-decoration:underline}
main{margin:30px 30px 60px 322px;max-width:1280px;padding:42px 50px;background:white;border:1px solid var(--line);border-radius:12px}h1,h2,h3{line-height:1.34;scroll-margin-top:18px}h1{font-size:34px;letter-spacing:-.6px;margin-top:0}h2{font-size:25px;margin-top:52px;padding-top:22px;border-top:1px solid var(--line)}h3{font-size:19px;margin-top:30px}p{margin:13px 0}a{color:var(--brand);overflow-wrap:anywhere}blockquote{margin:20px 0;background:var(--soft);border-left:4px solid var(--brand);padding:11px 20px}
table{width:100%;border-collapse:collapse;margin:20px 0;font-size:14px;line-height:1.55}th,td{border:1px solid var(--line);padding:10px 12px;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{background:#E8F1F2;font-weight:650}tbody tr:nth-child(even){background:#F8FAFB}
img{display:block;max-width:100%;height:auto;margin:24px auto;border:1px solid var(--line);border-radius:8px;padding:10px;background:white}pre{overflow:auto;padding:17px 19px;border:1px solid var(--line);border-radius:7px;background:#F4F7F8;font-size:13px;line-height:1.6}code{font-family:Consolas,monospace}li{margin:6px 0}.source{color:var(--muted);font-size:13px;border-bottom:1px solid var(--line);padding-bottom:18px;margin-bottom:30px}
@media(max-width:1100px){aside{position:static;width:auto}nav{columns:2}main{margin:18px;padding:25px}}@media(max-width:650px){body{font-size:15px}nav{columns:1}main{margin:0;border:0;border-radius:0;padding:22px 15px}table{display:block;overflow-x:auto}h1{font-size:28px}}
@media print{aside,.source{display:none}body{background:white;font-size:9.5pt}main{margin:0;padding:0;border:0;max-width:none}h2,h3{break-after:avoid}img,tr{break-inside:avoid}a{color:inherit}table{font-size:7.8pt}}
</style></head><body><aside><strong>OP Points × ELLIS × Giftronaut</strong><small>Integration BRD/PRD · v1.0</small><nav>__NAV__</nav></aside><main><p class="source">Bản đọc cục bộ · <a href="OP-POINTS-ELLIS-GIFTRONAUT-INTEGRATION-BRD-PRD.md">Markdown</a> · Diagram gồm PNG, SVG và PlantUML source.</p>__BODY__</main></body></html>"""
    target = ROOT / "OP-POINTS-ELLIS-GIFTRONAUT-INTEGRATION-BRD-PRD.html"
    template = template.replace("Integration BRD/PRD · v1.0", "Đặc tả tích hợp · v2.6 · 18/10/2026")
    template = template.replace('</style>', CSS + '</style>').replace('</body>', SCRIPT + '</body>')
    template = template.replace("Diagram gồm PNG, SVG và PlantUML source.", "Flow, API, exception, trạng thái và dữ liệu bàn giao Dev.")
    target.write_text(template.replace("__TITLE__", html.escape(TITLE)).replace("__NAV__", nav).replace("__BODY__", document), encoding="utf-8")
    print(f"HTML created; {len(ids)} headings and all local links checked.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jar", type=Path, default=ROOT.parents[2] / ".tools" / "plantuml-1.2025.2.jar")
    parser.add_argument("--html-only", action="store_true")
    args = parser.parse_args()
    if not args.html_only:
        if not args.jar.is_file():
            raise FileNotFoundError(f"PlantUML jar not found: {args.jar}")
        for output_format in ("png", "svg"):
            subprocess.run(["java", "-Djava.awt.headless=true", "-jar", str(args.jar.resolve()), "-charset", "UTF-8", "-failfast2", f"-t{output_format}", "-o", str(ROOT / "assets"), str(ROOT / "diagrams")], check=True)
        for source in (ROOT / "diagrams").glob("*.puml"):
            for extension in ("png", "svg"):
                output = ROOT / "assets" / f"{source.stem}.{extension}"
                if not output.is_file() or output.stat().st_size == 0:
                    raise ValueError(f"Missing rendered diagram: {output}")
        print("All PlantUML diagrams rendered as PNG and SVG.")
    build_html()


if __name__ == "__main__":
    main()

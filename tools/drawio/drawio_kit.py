"""draw.io の図を Python で組み立てて書き出すための小さなキット。

CLAUDE.md の「図の清書」の方針（配色・角丸・等幅フォント・アイコン）を部品にしたもの。
XML を手で書くとエスケープや base64 化で壊れやすいので、要素の多い図はこれで生成する。

使い方:
    import sys; sys.path.insert(0, "tools/drawio")
    from drawio_kit import Diagram, label, export_png

    d = Diagram("図の名前")
    d.box("a", label("タイトル", "説明", code="cmd"), 40, 40, 280, 64)
    d.box("b", "エラー", 40, 140, 280, 64, kind="error")
    d.edge("e1", "a", "b")
    d.save("pic/draw.io/<記事>/<図名>.drawio")
    export_png("pic/draw.io/<記事>/<図名>.drawio")

コマンドライン:
    python3 tools/drawio/drawio_kit.py export <file.drawio> [...]   # PNG を書き出す
    python3 tools/drawio/drawio_kit.py icons                        # 使えるアイコン一覧
"""

from __future__ import annotations

import base64
import html
import shutil
import subprocess
import sys
import urllib.request
import xml.dom.minidom
from pathlib import Path

# ---------------------------------------------------------------- 配色

# kind ごとの色。CLAUDE.md の「設計の方針」と対応している。
PALETTE: dict[str, dict[str, str]] = {
    "neutral": {"fill": "#FFFFFF", "stroke": "#9CA3AF", "font": "#1F2937", "sub": "#4B5563"},
    "muted":   {"fill": "#F9FAFB", "stroke": "#D1D5DB", "font": "#1F2937", "sub": "#4B5563"},
    "focus":   {"fill": "#EFF6FF", "stroke": "#3B82F6", "font": "#1E3A8A", "sub": "#4B5563"},
    "focus2":  {"fill": "#FFFFFF", "stroke": "#93C5FD", "font": "#1E3A8A", "sub": "#4B5563"},
    "error":   {"fill": "#FEF2F2", "stroke": "#DC2626", "font": "#991B1B", "sub": "#B91C1C"},
    "fix":     {"fill": "#ECFDF5", "stroke": "#059669", "font": "#065F46", "sub": "#047857"},
    "success": {"fill": "#059669", "stroke": "none",    "font": "#FFFFFF", "sub": "#D1FAE5"},
}
EDGE_COLOR = {"neutral": "#6B7280", "focus": "#3B82F6", "error": "#DC2626", "fix": "#059669"}
CODE_COLOR = "#6B7280"
MONO = "font-family:Menlo,monospace"

# ---------------------------------------------------------------- アイコン

# 版を固定した取得先。devicon は MIT、Simple Icons は CC0（ロゴ自体は各プロジェクトの商標）。
_DEVICON = "https://cdn.jsdelivr.net/gh/devicons/devicon@v2.16.0/icons/{0}/{0}-original.svg"
_SIMPLE = "https://cdn.jsdelivr.net/npm/simple-icons@13.21.0/icons/{0}.svg"

# 名前 -> (URL, 塗り色)。Simple Icons は単色なのでブランド色を付ける。
ICONS: dict[str, tuple[str, str | None]] = {
    "python":     (_DEVICON.format("python"), None),
    "jupyter":    (_DEVICON.format("jupyter"), None),
    "matplotlib": (_DEVICON.format("matplotlib"), None),
    "linux":      (_DEVICON.format("linux"), None),
    "docker":     (_DEVICON.format("docker"), None),
    "github":     (_DEVICON.format("github"), None),
    "git":        (_DEVICON.format("git"), None),
    "bash":       (_DEVICON.format("bash"), None),
    "vscode":     (_DEVICON.format("vscode"), None),
    "rust":       (_DEVICON.format("rust"), None),
    "nodejs":     (_DEVICON.format("nodejs"), None),
    "uv":         (_SIMPLE.format("uv"), "#DE5FE9"),
}
ICON_CACHE = Path(__file__).resolve().parent / ".cache" / "icons"


def icon_data_uri(name: str) -> str:
    """アイコンを取得（初回のみダウンロードしてキャッシュ）し、draw.io の style 用 data URI にする。"""
    if name not in ICONS:
        raise KeyError(f"未登録のアイコン: {name}（ICONS に URL を追加する）")
    url, fill = ICONS[name]
    path = ICON_CACHE / f"{name}.svg"
    if not path.exists():
        ICON_CACHE.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=20) as r:
            path.write_bytes(r.read())
    svg = path.read_text(encoding="utf-8")
    if "<script" in svg.lower():
        raise ValueError(f"{name}.svg に script が含まれている")
    if fill and "fill=" not in svg.split(">", 1)[0]:
        svg = svg.replace("<svg ", f'<svg fill="{fill}" ', 1)
    # draw.io の style は ; 区切りなので ";base64" は書かない（draw.io の流儀）
    return "data:image/svg+xml," + base64.b64encode(svg.encode()).decode()


# ---------------------------------------------------------------- ラベル

def code(text: str, size: int = 12, color: str = CODE_COLOR) -> str:
    """等幅フォントの span。text はエスケープされる。"""
    return f'<span style="font-size:{size}px;color:{color};{MONO}">{html.escape(text)}</span>'


def label(title: str, sub: str | None = None, code_text: str | None = None,
          kind: str = "neutral", title_size: int = 15, sub_size: int = 13) -> str:
    """「見出し1行＋説明1行（＋コード1行）」のラベル。title / sub には <b> などの HTML を書ける。"""
    p = PALETTE[kind]
    s = f'<b style="font-size:{title_size}px;color:{p["font"]}">{title}</b>'
    if sub:
        s += f'<br><span style="font-size:{sub_size}px;color:{p["sub"]}">{sub}</span>'
    if code_text:
        s += "<br>" + code(code_text)
    return s


# ---------------------------------------------------------------- 図

def _style(base: str, **extra: object) -> str:
    return base + "".join(f"{k}={v};" for k, v in extra.items())


class Diagram:
    """mxGraphModel を組み立てる。座標は絶対値（parent を指定したら親からの相対値）。"""

    def __init__(self, name: str, background: str = "#FFFFFF"):
        self.name = name
        self.background = background
        self.cells: list[str] = []
        self.ids: set[str] = set()

    # -- 低レベル
    def _add(self, id: str, xml_: str) -> str:
        if id in self.ids:
            raise ValueError(f"id が重複している: {id}")
        self.ids.add(id)
        self.cells.append(xml_)
        return id

    def vertex(self, id: str, value: str, style: str, x: float, y: float, w: float, h: float,
               parent: str = "1") -> str:
        return self._add(id,
            f'<mxCell id="{id}" value="{html.escape(value, quote=True)}" style="{style}" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')

    def edge(self, id: str, source: str, target: str, value: str = "", kind: str = "neutral",
             width: float = 1.5, dashed: bool = False, arrow: bool = True, orthogonal: bool = False,
             exit: tuple[float, float] | None = None, entry: tuple[float, float] | None = None,
             points: list[tuple[float, float]] | None = None, parent: str = "1", **extra: object) -> str:
        """矢印。exit / entry は (x, y) の比率（0〜1）。斜めになるときに指定して水平・垂直にそろえる。"""
        color = EDGE_COLOR.get(kind, kind)
        st = (f"html=1;rounded=1;strokeColor={color};strokeWidth={width};fontSize=12;"
              f"fontColor={PALETTE.get(kind, PALETTE['neutral'])['font']};labelBackgroundColor=#FFFFFF;")
        st += "endArrow=block;endSize=7;" if arrow else "endArrow=none;"
        if dashed:
            st += "dashed=1;dashPattern=4 3;"
        if orthogonal:
            st += "edgeStyle=orthogonalEdgeStyle;"
        if exit:
            st += f"exitX={exit[0]};exitY={exit[1]};exitDx=0;exitDy=0;"
        if entry:
            st += f"entryX={entry[0]};entryY={entry[1]};entryDx=0;entryDy=0;"
        st = _style(st, **extra)
        pts = ""
        if points:
            pts = '<Array as="points">' + "".join(f'<mxPoint x="{a}" y="{b}"/>' for a, b in points) + "</Array>"
        return self._add(id,
            f'<mxCell id="{id}" value="{html.escape(value, quote=True)}" style="{st}" edge="1" '
            f'source="{source}" target="{target}" parent="{parent}">'
            f'<mxGeometry relative="1" as="geometry">{pts}</mxGeometry></mxCell>')

    # -- 部品
    def box(self, id: str, value: str, x: float, y: float, w: float, h: float, kind: str = "neutral",
            align: str = "center", dashed: bool = False, width: float | None = None,
            parent: str = "1", **extra: object) -> str:
        """角丸の箱。kind は PALETTE のキー。"""
        p = PALETTE[kind]
        sw = width if width is not None else (2 if kind in ("focus", "error", "fix") else 1)
        st = (f"rounded=1;arcSize=12;whiteSpace=wrap;html=1;fontSize=14;align={align};verticalAlign=middle;"
              f"fillColor={p['fill']};strokeColor={p['stroke']};fontColor={p['font']};strokeWidth={sw};")
        if align == "left":
            st += "spacingLeft=12;"
        if dashed:
            st += "dashed=1;"
        return self.vertex(id, value, _style(st, **extra), x, y, w, h, parent)

    def pill(self, id: str, text: str, x: float, y: float, w: float, h: float = 32,
             kind: str = "success", font_size: int = 13, parent: str = "1") -> str:
        """塗りつぶしのピル（結果・タグ用）。"""
        p = PALETTE[kind]
        fill = p["fill"] if kind == "success" else p["stroke"]  # 枠の色で塗りつぶす
        st = (f"rounded=1;arcSize=50;html=1;fontSize={font_size};fontStyle=1;"
              f"fillColor={fill};strokeColor=none;fontColor=#FFFFFF;")
        return self.vertex(id, html.escape(text), st, x, y, w, h, parent)

    def group(self, id: str, x: float, y: float, w: float, h: float, kind: str = "focus",
              title: str | None = None, dashed: bool = True, parent: str = "1") -> str:
        """関連する要素を囲む枠。title はタイトル付きコンテナ（子は parent=id で相対座標）。"""
        p = PALETTE[kind]
        if title:
            st = (f"swimlane;startSize=36;rounded=1;arcSize=6;html=1;fontSize=14;fontStyle=1;"
                  f"fontColor={p['font']};fillColor={p['fill']};swimlaneFillColor=#FFFFFF;strokeColor={p['stroke']};")
            return self.vertex(id, html.escape(title), st, x, y, w, h, parent)
        st = f"rounded=1;arcSize=6;html=1;fillColor=#F5F9FF;strokeColor={p['stroke']};strokeWidth=1.5;"
        if dashed:
            st += "dashed=1;dashPattern=6 4;"
        return self.vertex(id, "", st, x, y, w, h, parent)

    def icon(self, id: str, name: str, x: float, y: float, size: float = 44, parent: str = "1") -> str:
        st = f"shape=image;image={icon_data_uri(name)};aspect=fixed;imageAspect=1;html=1;"
        return self.vertex(id, "", st, x, y, size, size, parent)

    def band(self, id: str, value: str, x: float, y: float, w: float, h: float = 100,
             kind: str = "muted", icon: str | None = None, icon_size: float = 44) -> str:
        """左端にアイコンを置いた横長の帯（層の表現用）。"""
        p = PALETTE[kind]
        sw = 2 if kind == "focus" else 1
        st = (f"rounded=1;arcSize=10;whiteSpace=wrap;html=1;align=left;verticalAlign=middle;"
              f"spacingLeft={96 if icon else 24};fillColor={p['fill']};strokeColor={p['stroke']};strokeWidth={sw};")
        self.vertex(id, value, st, x, y, w, h)
        if icon:
            self.icon(f"{id}_icon", icon, x + 28, y + (h - icon_size) / 2, icon_size)
        return id

    def marker(self, id: str, cx: float, cy: float, text: str = "✕", kind: str = "error", r: float = 13) -> str:
        """線の上に置く丸いマーカー（✕＝ここで途切れる、など）。"""
        color = PALETTE[kind]["stroke"]
        st = (f"ellipse;html=1;fontSize=14;fontStyle=1;fillColor={color};strokeColor=#FFFFFF;"
              f"strokeWidth=2;fontColor=#FFFFFF;")
        return self.vertex(id, html.escape(text), st, cx - r, cy - r, 2 * r, 2 * r)

    def callout(self, id: str, title: str, x: float, y: float, w: float = 270, h: float = 68,
                code_text: str | None = None, kind: str = "error") -> str:
        """原因＋確認コマンドの注記。title には <br> を書ける。"""
        value = f"<b>{title}</b>"
        if code_text:
            value += "<br>" + code(f"確認: {code_text}")
        return self.box(id, value, x, y, w, h, kind=kind, align="left", width=1, fontSize=13)

    def text(self, id: str, value: str, x: float, y: float, w: float, h: float = 20,
             align: str = "left", size: int = 12, color: str = CODE_COLOR) -> str:
        st = f"text;html=1;align={align};verticalAlign=middle;fontSize={size};fontColor={color};"
        return self.vertex(id, value, st, x, y, w, h)

    # -- 出力
    def to_xml(self) -> str:
        return (f'<mxfile host="drawio"><diagram id="d1" name="{html.escape(self.name, quote=True)}">'
                f'<mxGraphModel grid="0" page="0" background="{self.background}"><root>'
                '<mxCell id="0"/><mxCell id="1" parent="0"/>'
                + "".join(self.cells) + "</root></mxGraphModel></diagram></mxfile>")

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        xml_ = self.to_xml()
        xml.dom.minidom.parseString(xml_)  # 壊れた XML を書き出さない
        path.write_text(xml_, encoding="utf-8")
        return path


# ---------------------------------------------------------------- 図の型

def layer_stack(d: Diagram, layers: list[dict], fails: list[dict] | None = None,
                shortcut: dict | None = None, enclose: dict | None = None,
                x: float = 380, top: float = 84, width: float = 500, height: float = 100, gap: float = 28,
                path_label: str | None = None) -> dict[str, tuple[float, float]]:
    """層を積んだ図。下の層から上の層へ「通り道」を引き、境目に ✕ と注記を置く。

    layers: 上から順に {"id", "title", "sub", "code", "icon", "kind"}。kind の既定は "muted"
    fails:  {"between": (下の層のid, 上の層のid), "title", "code"} — 通り道がその境目で途切れる原因
    shortcut: {"title", "sub", "icon", "target": 層のid, "label", "y", "w"} — 層を飛ばして直接届く経路（右側、緑）。
              見出しが折り返すときは w（既定 300）を広げる
    enclose: {"ids": [層のid, ...], "tag": 文字列} — 層をまとめて囲む青い破線とタグ
    返り値: 層の id -> (上端 y, 下端 y)
    """
    span: dict[str, tuple[float, float]] = {}
    y = top
    for L in layers:
        kind = L.get("kind", "muted")
        lk = "focus" if kind in ("focus", "focus2") else "neutral"
        d.band(L["id"], label(L["title"], L.get("sub"), L.get("code"), kind=lk), x, y, width, height,
               kind=kind, icon=L.get("icon"))
        span[L["id"]] = (y, y + height)
        y += height + gap

    if enclose:
        ys = [span[i] for i in enclose["ids"]]
        y0, y1 = min(a for a, _ in ys), max(b for _, b in ys)
        d.group("enclose", x - 16, y0 - 20, width + 32, y1 - y0 + 34, kind="focus")
        d.cells.insert(0, d.cells.pop())  # 囲みを帯より背面に置く
        if enclose.get("tag"):
            d.pill("enclose_tag", enclose["tag"], x + width - 300, y0 - 32, 300, 26, kind="focus", font_size=12)

    ids = [L["id"] for L in layers]
    px = x - 44
    bottom, topmost = ids[-1], ids[0]
    d.edge("font_path", bottom, topmost, kind="neutral", width=3, orthogonal=True, exit=(0, 0.5), entry=(0, 0.5),
           points=[(px, sum(span[bottom]) / 2), (px, sum(span[topmost]) / 2)])
    if path_label:
        d.text("font_path_label", path_label, px - 6, span[bottom][1] + 12, 420)

    for i, f in enumerate(fails or []):
        lo, hi = f["between"]
        cy = (span[hi][1] + span[lo][0]) / 2
        mid = d.marker(f"fail{i}_x", px, cy)
        cid = d.callout(f"fail{i}", f["title"], x - 350, cy - 34, code_text=f.get("code"))
        d.edge(f"fail{i}_l", cid, mid, kind="error", width=1, arrow=False, dashPattern="2 3", dashed=True)

    if shortcut:
        sx, sy = x + width + 60, shortcut.get("y", span[shortcut["target"]][0] + 144)
        d.box("shortcut", label(shortcut["title"], shortcut.get("sub"), kind="fix"), sx, sy,
              shortcut.get("w", 300), 72,
              kind="fix", align="left", dashed=True, spacingLeft=64)
        if shortcut.get("icon"):
            d.icon("shortcut_icon", shortcut["icon"], sx + 14, sy + 18, 36)
        d.edge("shortcut_e", "shortcut", shortcut["target"], shortcut.get("label", ""), kind="fix", width=3,
               orthogonal=True, exit=(0.5, 0), entry=(1, 0.5))
    return span


# ---------------------------------------------------------------- 書き出し

def find_drawio() -> str:
    """draw.io Desktop の CLI を探す。"""
    for c in (shutil.which("drawio"), "/Applications/draw.io.app/Contents/MacOS/draw.io"):
        if c and Path(c).exists():
            return c
    raise FileNotFoundError("draw.io Desktop が見つからない（https://github.com/jgraph/drawio-desktop）")


def export_png(src: str | Path, scale: int = 2, border: int = 16) -> Path:
    """XML を埋め込んだ PNG（<名前>.drawio.png）を書き出す。PNG を draw.io で開けば再編集できる。"""
    src = Path(src)
    out = src.with_name(src.name + ".png")
    subprocess.run([find_drawio(), "-x", "-f", "png", "-e", "-b", str(border), "-s", str(scale),
                    "-o", str(out), str(src)], check=True, capture_output=True)
    return out


def _main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "export":
        for p in argv[1:]:
            print(export_png(p))
        return 0
    if argv[:1] == ["icons"]:
        for k, (url, _) in ICONS.items():
            print(f"{k:12} {url}")
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))

# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Qiita の記事（public/*.md）と画像（pic/）を検査する。

markdownlint では分からない、Qiita とこのリポジトリ固有の決まりを見る。

    uv run tools/check_articles.py        # リポジトリのルートで実行（make lint からも呼ばれる）

エラー（終了コード 1）:
- ファイル名が kebab-case でない（Qiita のエディタで書いた記事は <id>.md で入ってくる）
- front matter が無い・title が空・タグが 1〜5 個でない・空のタグがある
- id が 20 桁の英数字でない、または同じ id の記事が複数ある
- 画像の URL が https:// で始まっていない（ローカルのパスは Qiita で表示されない）
- `<!-- 図の元: パス -->` のファイルが無い
- pic/draw.io/<フォルダ>/ と同じ名前の記事が無い
- pic/ の写真に位置情報（EXIF の GPS）が残っている（公開リポジトリなので、撮影場所が分かってしまう）
"""
from __future__ import annotations

import os
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
PIC = ROOT / "pic"
DRAWIO = PIC / "draw.io"

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ID_RE = re.compile(r"^[0-9a-f]{20}$")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)|<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']", re.I)
SOURCE_RE = re.compile(r"<!--\s*図の元:\s*(\S+?)\s*-->")
FENCE_RE = re.compile(r"^\s*(```|~~~)")

IN_ACTIONS = os.environ.get("GITHUB_ACTIONS") == "true"


class Report:
    def __init__(self) -> None:
        self.errors = 0
        self.warnings = 0

    def _emit(self, level: str, path: Path, line: int | None, msg: str) -> None:
        rel = path.relative_to(ROOT)
        where = f"{rel}:{line}" if line else f"{rel}"
        print(f"{'エラー' if level == 'error' else '警告'}: {where}: {msg}")
        if IN_ACTIONS:  # PR の差分の該当行に注釈を出す
            loc = f"file={rel}" + (f",line={line}" if line else "")
            print(f"::{level} {loc}::{msg}")

    def error(self, path: Path, line: int | None, msg: str) -> None:
        self.errors += 1
        self._emit("error", path, line, msg)

    def warn(self, path: Path, line: int | None, msg: str) -> None:
        self.warnings += 1
        self._emit("warning", path, line, msg)


def parse_front_matter(text: str) -> tuple[dict[str, str], list[str]] | None:
    """front matter の単純な key: value と tags の一覧を返す（YAML ライブラリを使わない）。"""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = lines.index("---", 1)
    except ValueError:
        return None
    fields: dict[str, str] = {}
    tags: list[str] = []
    current = None
    for raw in lines[1:end]:
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", raw)
        if m:
            current = m.group(1)
            fields[current] = m.group(2).strip()
            continue
        m = re.match(r"^\s+-\s*(.*)$", raw)
        if m and current == "tags":
            tags.append(m.group(1).strip())
    return fields, tags


def unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def body_lines(text: str):
    """コードブロックの外の行だけを (行番号, 行) で返す。"""
    in_fence = False
    for no, line in enumerate(text.splitlines(), 1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield no, line


def check_article(path: Path, report: Report, ids: dict[str, Path]) -> None:
    if ID_RE.match(path.stem):
        report.error(path, None, "ファイル名が記事の id のまま（Qiita から取り込んだ記事は、内容が分かる名前に変えてからマージする）")
    elif not NAME_RE.match(path.stem):
        report.error(path, None, "ファイル名は英小文字・数字をハイフンでつなぐ（kebab-case）")

    text = path.read_text(encoding="utf-8")
    parsed = parse_front_matter(text)
    if parsed is None:
        report.error(path, 1, "front matter（--- で囲んだ部分）が無い")
        return
    fields, tags = parsed

    if not unquote(fields.get("title", "")).strip():
        report.error(path, None, "title が空")
    if not 1 <= len(tags) <= 5:
        report.error(path, None, f"タグは 1〜5 個（今は {len(tags)} 個）")
    if any(not unquote(t).strip() for t in tags):
        report.error(path, None, "空のタグがある（qiita new 直後の '' のまま）")

    item_id = unquote(fields.get("id", "null"))
    if item_id not in ("null", "~", ""):
        if not ID_RE.match(item_id):
            report.error(path, None, f"id の形式が違う: {item_id}")
        elif item_id in ids:
            report.error(path, None, f"id が {ids[item_id].name} と重複している: {item_id}")
        else:
            ids[item_id] = path

    for no, line in body_lines(text):
        for m in IMAGE_RE.finditer(line):
            url = m.group(1) or m.group(2)
            if not url.startswith("https://"):
                report.error(path, no, f"画像は https:// の URL にする（Qiita で表示されない）: {url}")
        for m in SOURCE_RE.finditer(line):
            if not (ROOT / m.group(1)).is_file():
                report.error(path, no, f"図の元のファイルが無い: {m.group(1)}")


GPS_IFD_TAG = 0x8825


def exif_block(data: bytes) -> bytes | None:
    """JPEG の APP1（Exif）か PNG の eXIf チャンクから、TIFF 形式の EXIF を取り出す。"""
    if data.startswith(b"\xff\xd8"):
        i = data.find(b"Exif\x00\x00")
        return data[i + 6:] if i >= 0 else None
    if data.startswith(b"\x89PNG"):
        i = data.find(b"eXIf")
        return data[i + 4:] if i >= 0 else None
    return None


def has_gps(path: Path) -> bool:
    """EXIF の最初の IFD に GPS の項目があるか。"""
    tiff = exif_block(path.read_bytes())
    if not tiff or tiff[:2] not in (b"II", b"MM"):
        return False
    bo = "<" if tiff[:2] == b"II" else ">"
    try:
        (offset,) = struct.unpack_from(bo + "I", tiff, 4)
        (count,) = struct.unpack_from(bo + "H", tiff, offset)
        return any(
            struct.unpack_from(bo + "H", tiff, offset + 2 + 12 * k)[0] == GPS_IFD_TAG
            for k in range(count)
        )
    except struct.error:  # 壊れた EXIF は判定しない
        return False


def check_pictures(report: Report, names: set[str]) -> None:
    if DRAWIO.is_dir():
        for folder in sorted(p for p in DRAWIO.iterdir() if p.is_dir()):
            if folder.name not in names:
                report.error(folder, None, "同じ名前の記事が public/ に無い（フォルダ名は記事のファイル名から .md を除いたもの）")
    if PIC.is_dir():
        for img in sorted(PIC.rglob("*")):
            if img.suffix.lower() in (".jpg", ".jpeg", ".png") and not img.name.endswith(".drawio.png"):
                if has_gps(img):
                    report.error(img, None, "写真に位置情報（EXIF の GPS）が残っている。消してからコミットする")


def main() -> int:
    report = Report()
    articles = sorted(PUBLIC.glob("*.md"))
    ids: dict[str, Path] = {}
    for path in articles:
        check_article(path, report, ids)
    check_pictures(report, {p.stem for p in articles})
    print(f"記事 {len(articles)} 本を検査：エラー {report.errors} 件、警告 {report.warnings} 件")
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())

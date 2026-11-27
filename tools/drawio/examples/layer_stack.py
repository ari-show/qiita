"""layer_stack() のお手本：Dockerfile で uv を使うときに「uv が見つからない」となる層。

    python3 tools/drawio/examples/layer_stack.py   # リポジトリのルートで実行

層（帯）を上から並べ、下から上への「通り道」が途切れる境目に ✕ と原因・確認コマンドを置く。
右側の近道は、層を飛ばして直接届く方法を示す。
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from drawio_kit import Diagram, export_png, layer_stack  # noqa: E402

d = Diagram("uv が見つかるまで")
layer_stack(
    d,
    layers=[
        {"id": "run", "title": "uv sync", "sub": "Dockerfile の RUN で依存パッケージを入れる",
         "code": "RUN uv sync", "icon": "uv", "kind": "focus"},
        {"id": "path", "title": "シェルの PATH", "sub": "コマンド名から実行ファイルを探す",
         "code": 'ENV PATH="/root/.local/bin:$PATH"', "icon": "bash", "kind": "focus2"},
        {"id": "dest", "title": "インストール先", "sub": "インストーラが uv を置く場所（XDG 準拠）",
         "code": "~/.local/bin/uv", "icon": "linux"},
    ],
    fails=[
        {"between": ("dest", "path"), "title": "PATH に ~/.local/bin が無い", "code": "echo $PATH"},
        {"between": ("path", "run"), "title": "古い手順の<br>. $HOME/.cargo/env が失敗", "code": "ls ~/.cargo/env"},
    ],
    enclose={"ids": ["run", "path"], "tag": "Dockerfile で設定する範囲"},
    shortcut={"title": "COPY --from=ghcr.io/astral-sh/uv", "sub": "公式イメージから /bin に直接コピー",
              "icon": "docker", "target": "run", "w": 380, "label": "PATH 上の /bin に置くので<br>インストール先に依存しない"},
    path_label="uv の実行ファイルが見つかるまで（下から上へ）",
)
out = d.save(HERE / "layer_stack.drawio")
print(export_png(out, border=20))

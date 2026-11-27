# CLAUDE.md

Qiita CLI で記事を管理するリポジトリ。

## 構成

- `public/*.md` — 記事本体（Qiita CLI 管理。front matter の `id` / `updated_at` は手で書き換えない）
  - ファイル名は英小文字・数字をハイフンでつなぐ（kebab-case。例: `uv-xdg-compliant.md`）。Qiita CLI は記事を `id` で探すので、名前を変えても Qiita 側には影響しない
- `pic/` — 記事用の画像の元データ。Qiita へのアップロードは手動
- `pic/draw.io/<記事>/` — draw.io の図。記事ごとにフォルダを分ける（下記）
- `tools/drawio/` — 図を Python で組み立てるキット `drawio_kit.py` と、そのお手本 `examples/`
- `tmp/` — 下書き置き場。コミットしない
- `Makefile` — よく使う操作。`make` で一覧を表示する

### よく使うコマンド

```bash
make new name=my-article   # 記事を作る（ファイル名の規則を検査してから qiita new）
make preview               # ブラウザでプレビュー（http://localhost:8888）
make pull                  # Qiita 側の記事を取り込む
make check-names           # public/ のファイル名が規則どおりか調べる
```

- Python のスクリプトは `uv run` で実行する（スクリプト先頭の PEP 723 のメタデータで Python の版を決めている。外部パッケージは使っていない）
- 記事の公開（`qiita publish`）は取り消しにくいので Makefile には入れていない。ユーザーに確認してから実行する

### 図の置き場所

```
pic/draw.io/
  <記事>/                     記事ファイル名から .md を除いた名前（例: uv-xdg-compliant）
    <図名>.drawio             編集用（正本）
    <図名>.drawio.png         記事に貼る PNG（XML 埋め込み。draw.io で開き直せる）
    <図名>.py                 スクリプトで生成した図はその生成元も置く
tools/drawio/
  drawio_kit.py               配色・部品・図の型・書き出し
  examples/                   お手本（スクリプトと生成結果）
  .cache/                     取得したアイコン（コミットしない）
```

- 記事がまだ `tmp/` の下書きの段階では、図も `tmp/` に置く。記事を `public/` に移すときに `pic/draw.io/<記事>/` へ移す。
- `pic/draw.io/` 直下にある古い図は、このルールより前のもの。触るついでに記事フォルダへ移してよい。

## 図の清書（draw.io）

Qiita は ```` ```mermaid ```` をそのまま表示できる。Mermaid で足りる図は Mermaid のままにし、
「見やすくしたい」図だけ draw.io で清書する。

清書は **Mermaid を変換するのではなく、draw.io XML を直接書いて設計する**。
Mermaid から変換すると Mermaid の見た目と自動配置がそのまま残り、清書にならない。
Mermaid は内容の下書き（何をつなぐか）として使い、配置と色は以下の方針で決め直す。

### 設計の方針

1. **先に「この図で何を一番伝えたいか」を1文で決める**。それが一目で見える配置にする。
   - 例：「同じコマンドでも、PR 以前と以後で結果が変わる」→ 以前と以後を左右に並べ、同じ手順を同じ高さに置く
   - 比較なら左右に並べる、手順なら上から下に流す、構成ならグループ（コンテナ）で囲む
2. **色は意味のある箇所だけに使う**。それ以外はグレーと白。
   - 通常：枠 `#9CA3AF`、塗り `#FFFFFF`、文字 `#1F2937`
   - 変更点・注目：青（枠 `#3B82F6`、塗り `#EFF6FF`、文字 `#1E3A8A`）
   - エラー：赤（枠 `#DC2626`、塗り `#FEF2F2`、文字 `#991B1B`）
   - 修正・対処：緑の破線（枠 `#059669`、塗り `#ECFDF5`、`dashed=1`）
   - 結果・成功：緑で塗りつぶしたピル型（`arcSize=50`、塗り `#059669`、白文字）
3. パス・コマンド・コードは `<font face="Menlo">` で等幅にする。
4. 枠の中身は「見出し1行＋詳細1行」まで。長い説明は記事本文に書く。
5. 図の中の矢印や比較線にも短いラベルを付け、関係を言葉にする（例：「PR #8420 で変更」）。
6. 背景は白（`background="#FFFFFF"`）にし、角は丸める（`rounded=1;arcSize=14`）。

7. 層構造の話（OS → 環境 → プロセス → ライブラリなど）は、**下から上へ積んだ帯**で描く。「どこで途切れると失敗するか」は層の境目に赤い ✕ と注記（原因＋確認コマンド）を置く。
8. 登場するツールには**ロゴアイコン**を添える（帯の左端に 40〜44px）。
   - draw.io 内蔵ライブラリに無いロゴ（Python・Jupyter・Matplotlib・Linux など）は devicon（MIT）を、devicon に無いもの（uv など）は Simple Icons（CC0）を使う。CDN から版を固定して取得する
     - `https://cdn.jsdelivr.net/gh/devicons/devicon@v2.16.0/icons/<名前>/<名前>-original.svg`
     - `https://cdn.jsdelivr.net/npm/simple-icons@13.21.0/icons/<名前>.svg`（単色なので `fill` でブランド色を付ける）
   - `.drawio` 単体で表示できるよう、`shape=image;image=data:image/svg+xml,<base64>;aspect=fixed;` で埋め込む

お手本：
- 比較（XML を手書き）：`pic/draw.io/uv-xdg-compliant/uvのインストール先変更.drawio`
- 層構造＋アイコン（キットで生成）：`tools/drawio/examples/layer_stack.py`

### draw.io CLI

`drawio` が PATH に無ければ、次のフルパスを使う。

```
/Applications/draw.io.app/Contents/MacOS/draw.io
```

### 手順

1. 上の方針に沿って `pic/draw.io/<記事>/<図名>.drawio` を作る。
   - 要素が多い図やアイコンを入れる図は、XML を手で書かず `tools/drawio/drawio_kit.py` を使ったスクリプト（`<図名>.py`）で生成する。配色は方針どおりの `kind`（`neutral` / `focus` / `error` / `fix` / `success`）で指定でき、エスケープ・アイコンの base64 化・XML の検証も任せられる
   - 層構造の図は `layer_stack()` を使う（`tools/drawio/examples/layer_stack.py` を参照）
   - 使えるアイコンは `make icons`（`uv run tools/drawio/drawio_kit.py icons`）。足りなければ `ICONS` に版を固定した URL を追加する
   - XML の書き方は https://raw.githubusercontent.com/jgraph/drawio-mcp/main/shared/xml-essentials.md に従う
   - 座標を自分で決めにくい図（ネットワーク図など）は `--layout verticalFlow` などで自動配置してよい
2. XML を埋め込んだ PNG を書き出す（`-e` を付けると、PNG を draw.io で開いて再編集できる）。
   ```bash
   make diagram f="pic/draw.io/<記事>/<図名>.drawio"
   # = uv run tools/drawio/drawio_kit.py export "pic/draw.io/<記事>/<図名>.drawio"
   # 中身は: drawio -x -f png -e -b 16 -s 2 -o "<図名>.drawio.png" "<図名>.drawio"
   ```
3. 書き出した PNG を必ず目で確認する（文字のはみ出し、線とラベルの重なり、余白の偏り）。崩れていれば XML を直して手順 2 からやり直す。

素早く形だけ作りたいときは、Mermaid を `.drawio` に変換して（`drawio -x -f xml -o x.drawio x.mmd`）たたき台にしてもよい。ただしそのまま完成にはせず、上の方針で直す。

### 注意

- `.drawio` の XML を `sed` で置換しない。値に含まれる `&lt;` などの `&` が「マッチした文字列」に展開されて XML が壊れ、矢印が消える。部分的に直すときは Edit ツールか Python を使う。
- 矢印が斜めになるときは、`exitX/exitY`・`entryX/entryY` で接続位置を指定して水平・垂直にそろえる。
- 記事への貼り付け：Qiita のエディタに PNG をドラッグして取得した URL を `![説明](URL)` で書く。Qiita CLI は画像をアップロードしないので、ここはユーザーが手でやる。URL をでっち上げない。
- 外部送信：Desktop CLI での変換・書き出しはローカルで完結する。キットがアイコンを取りに行くのは jsDelivr の CDN だけ（図の内容は送らない）。drawio プラグインの `create_diagram`（`mcp.draw.io`）は図の内容を外部に送るので、このリポジトリでは使わない。

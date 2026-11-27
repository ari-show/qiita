# 記事と図の作業をまとめたコマンド。`make` だけで一覧を表示する。
# 記事の公開（qiita publish）は取り消しにくいので、ここには入れない。

.DEFAULT_GOAL := help

# 記事のファイル名の規則：英小文字・数字をハイフンでつなぐ（kebab-case）
NAME_RE := ^[a-z0-9]+(-[a-z0-9]+)*$$

.PHONY: help install new preview pull check-names icons diagram

help: ## コマンドの一覧を表示する
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-12s %s\n", $$1, $$2}'

install: ## 依存パッケージを入れる（package-lock.json どおり）
	npm ci

new: ## 記事を作る（例: make new name=my-article）
	@test -n "$(name)" || { echo "name を指定してください（例: make new name=my-article）"; exit 1; }
	@echo "$(name)" | grep -Eq '$(NAME_RE)' || { echo "ファイル名は英小文字・数字・ハイフンにしてください: $(name)"; exit 1; }
	@test ! -e "public/$(name).md" || { echo "すでにあります: public/$(name).md"; exit 1; }
	npx qiita new "$(name)"

preview: ## ブラウザでプレビューする（http://localhost:8888）
	npx qiita preview

pull: ## Qiita 側の記事を手元に取り込む
	npx qiita pull

check-names: ## public/ の記事のファイル名が規則どおりか調べる
	@bad=$$(ls public/*.md | xargs -n1 basename | sed 's/\.md$$//' | grep -Ev '$(NAME_RE)'); \
	if [ -n "$$bad" ]; then echo "規則に合わないファイル名:"; echo "$$bad" | sed 's/^/  /'; exit 1; fi; \
	echo "OK: すべて規則どおり"

icons: ## 図に使えるアイコンの一覧
	uv run tools/drawio/drawio_kit.py icons

diagram: ## 図を PNG に書き出す（例: make diagram f="pic/draw.io/<記事>/<図名>.drawio"）
	@test -n "$(f)" || { echo 'f を指定してください（例: make diagram f="pic/draw.io/<記事>/<図名>.drawio"）'; exit 1; }
	uv run tools/drawio/drawio_kit.py export "$(f)"

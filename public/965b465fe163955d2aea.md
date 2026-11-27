---
title: OrcaRouter GuardrailsでPIIをマスク・遮断する：入力／出力／日本固有形式を実測した記録
tags:
  - OrcaRouter
  - PII
private: false
updated_at: '2026-08-15T14:47:56+09:00'
id: 965b465fe163955d2aea
organization_url_name: null
slide: false
ignorePublish: false
posting_campaign_uuid: null
agreed_posting_campaign_term: false
---
LLMに渡すログや問い合わせ文には、メールアドレス、カード番号、電話番号、APIキーやトークンなどの秘密情報に見える文字列が混ざる。PII Guardrail を置くだけでは十分ではない。どの文字列を、**input**（モデルへ送る前）と **output**（モデル応答を返す前）のどちらで、`mask` と `block` のどちらとして扱うかを設定し、実際の表記で確かめる必要がある。

本記事では OrcaRouter の Guardrail を検証用API keyごとに分け、エコー応答を使って確認した。実在の個人情報・実在の秘密鍵は送っていない。pytestの「原文が応答にない／400で遮断された」という結果と、Matches feed の `stage`・`action`・`detail` を合わせて判定している。

## まず結果：何を検証し、何が分かったか


| 検証シナリオ                  | 設定した防御                          | live test                        | Matches feed      | 判断                 |
| ----------------------- | ------------------------------- | -------------------------------- | ----------------- | ------------------ |
| 標準PII（入力）               | input / mask、email・カード番号        | 2件 pass                          | input / mask を確認  | この合成値では有効          |
| 日本形式携帯番号（入力）            | input / mask、custom regex追加前    | fail                             | matchなし           | 標準設定では未検出          |
| 日本形式携帯番号（入力）            | input / mask、custom regex追加後    | 3件 pass                          | input / mask を確認  | 検証した表記では有効         |
| カード番号遮断                 | input / block                   | 1件 pass（400 `guardrail_blocked`） | input / block を確認 | 遮断を確認              |
| 日本形式携帯番号（出力）            | output / mask、custom regex追加後   | 3件 pass                          | output / mask を確認 | 検証した表記では有効         |




ここでいう「pass」は、マスク系では合成値の原文がcompletionに含まれないこと、block系ではHTTP 400かつ `guardrail_blocked` が返ることを意味する。エコー試験だけで「上流モデルが絶対に生値を見ていない」ことまでは証明できないため、Matches feed も確認できた行だけを Guardrail 発火まで確認済みとした。

## 共通の実験方法

テストは OpenAI互換の Chat Completions に、合成値を「そのまま返す」よう依頼して実行した。原文が応答に残れば fail、マスクされるか遮断されれば pass とする。live APIの実行は明示的に opt-in である。

```bash
ORCAROUTER_PII_TEST_PROFILE=<profile> \
ORCAROUTER_RUN_LIVE_TESTS=1 \
uv run pytest
```

誤検知を調べる場合は、正規表現に一致しない near-miss を送り、原文が残ることを確認した。

```bash
ORCAROUTER_PII_TEST_PROFILE=<profile> \
ORCAROUTER_PII_TEST_KIND=negative \
ORCAROUTER_RUN_LIVE_TESTS=1 \
uv run pytest
```

API keyの値、実在のPII、request ID、IP、match本文は記録していない。各profileとkey名の対応は以下に残している。

:::note info

<details><summary>guardrailのprofileについて</summary>

各プロファイルは **1つの検証用 API key と、その key に明示的に紐付けた Guardrail** の組です。キー値は `.env` にだけ置き、Guardrail の設定・Matches feed・pytest の結果を `evidence.md` に対応付けます。


| Profile    | `.env` のキー名                   | Template / stage / action               | live ケース                                        | 現在の状態                             |
| ---------- | ----------------------------- | --------------------------------------- | ----------------------------------------------- | --------------------------------- |
| `mask`     | `ORCAROUTER_API_KEY_MASK`     | PII Shield / input / mask               | email、カード、携帯番号                                  | **実測済み**                          |
| `block`    | `ORCAROUTER_API_KEY_BLOCK`    | PII Blocker / input / block             | カード                                             | **実測済み**                          |
| `output`   | `ORCAROUTER_API_KEY_OUTPUT`   | Response PII Redactor / output / mask   | email、カード、携帯番号                                  | **実測済み**                          |
| `jp_ids`   | `ORCAROUTER_API_KEY_JP_IDS`   | Custom Info Redactor / input / mask     | custom マイナンバー12桁形式、custom 郵便番号                  | custom rule は live 成功、Matches 未確認 |
| `identity` | `ORCAROUTER_API_KEY_IDENTITY` | custom / semantic policy / input / mask | 日本語氏名、住所                                        | 未設定・探索的                           |
| `secrets`  | `ORCAROUTER_API_KEY_SECRETS`  | Secrets Blocker / input / block         | OpenAI key 形式、AWS key 形式、JWT 形式、GitHub token 形式 | 初回 live は4 failed。実効設定を要確認        |


`ORCAROUTER_PII_TEST_PROFILE` は上表の Profile を指定する。指定しない場合は `mask` になる。profile ごとにテスト対象を固定しているため、設定していない entity を誤って live API へ送らない。

各 profile は既定で「検出されるべき」positive ケースを実行する。`ORCAROUTER_PII_TEST_KIND=negative` を指定すると、その profile の near-miss を送り、正常な値を mask / block していないことを確認する。negative 実行後は Matches feed に該当 entity の match がないことも確認する。

## コンソールで作る設定

### 既存の `mask` / `block`

この2つはすでに live で確認済みである。`mask` の custom entity `jp_mobile_phone` は、Guardrail の version、RE2 正規表現、mask tag を `evidence.md` へ追記する。

### `output`

1. `Response PII Redactor` template から Guardrail を作る。
2. `stage: output`、`action: mask` と、email / phone / credit_card を確認する。
3. `ORCAROUTER_API_KEY_OUTPUT` の key にだけ紐付ける。input rule を同じ key に混在させない。
4. raw-content logging は off にする。

### `jp_ids`

1. input / mask の PII rule を作る。
2. `jp_mynumber` は予約済みのため custom entity 名に使わない。初回 live test でも12桁ダミー値を検出できなかったため、built-in の対応を記事で主張しない。
3. custom entity を2つ追加する。名前・正規表現・mask tag はコンソールの生成 JSON を証拠として保存する。
  - `jp_mynumber_format`: `\b[0-9]{12}\b` で12桁**形式だけ**を扱う。番号の真正性は検証しない。
  - `jp_postal_code_format`: `\b[0-9]{3}-[0-9]{4}\b` で `123-4567` 形式を扱う。
4. `ORCAROUTER_API_KEY_JP_IDS` に紐付ける。

### `identity`

日本語氏名・住所は、単純な正規表現だけで網羅的・低誤検知に検出できるとは扱わない。利用する policy（custom regex、LLM judge、またはアプリ側二次防衛）を決めてから key を紐付ける。この profile の結果は、設定した限定的な表記にしか一般化しない。

### `secrets`

`Secrets Blocker` template から input / block の Guardrail を作る。これは PII Shield と分けて検証し、OpenAI / AWS / JWT / GitHub token の**合成値**を使う。実在する token や秘密鍵は使わない。

## 実行コマンド

live 実行の opt-in は `.env` に保存せず、毎回コマンドで渡す。

```bash
# 既存の input / mask 回帰
ORCAROUTER_PII_TEST_PROFILE=mask \
ORCAROUTER_RUN_LIVE_TESTS=1 \
uv run pytest

# 既存 custom phone の誤検知確認
ORCAROUTER_PII_TEST_PROFILE=mask \
ORCAROUTER_PII_TEST_KIND=negative \
ORCAROUTER_RUN_LIVE_TESTS=1 \
uv run pytest

# 既存の input / block
ORCAROUTER_PII_TEST_PROFILE=block \
ORCAROUTER_RUN_LIVE_TESTS=1 \
uv run pytest

# output / mask
ORCAROUTER_PII_TEST_PROFILE=output \
ORCAROUTER_RUN_LIVE_TESTS=1 \
uv run pytest

# 日本固有の形式
ORCAROUTER_PII_TEST_PROFILE=jp_ids \
ORCAROUTER_RUN_LIVE_TESTS=1 \
uv run pytest

# secrets の block
ORCAROUTER_PII_TEST_PROFILE=secrets \
ORCAROUTER_RUN_LIVE_TESTS=1 \
uv run pytest
```

`identity` は policy の検出範囲を決めるまで実行しない。各 run の直後に Matches feed で profile に対応する Guardrail の rule type・stage・action・entity・件数を確認し、raw match、request ID、key 値は保存しない。

</details>

:::

## シナリオ1：標準PII Shieldを入力でマスクする

### 設定

検証用の `mask` API key に、PII Shield の **input / mask** Guardrail（Matches上の名称: `article-0-4-input-mask-v1`）を紐付けた。対象は email と credit card、および後述する日本携帯番号のcustom entityである。

概念的には次の構成である。実際にはUIで作成・keyへattachmentした。

```json
{
  "rules": [{
    "type": "pii",
    "stage": "input",
    "action": "mask",
  }]
}
```

### 初回結果

`email` とカード番号はpassした一方、11桁・ハイフン付きの日本携帯番号形式はfailした。Matches feedにも email と credit card の `input / mask` だけが残り、電話番号のmatchはなかった。


| ケース         | pytest | Matches feed   |
| ----------- | ------ | -------------- |
| email       | pass   | `input / mask` |
| credit card | pass   | `input / mask` |
| 日本形式携帯番号    | fail   | matchなし        |


これは標準の `phone` entity 全般が機能しないことを示すものではない。**この表記を、この設定では検出できなかった**という範囲の結果である。

## シナリオ2：日本形式携帯番号をcustom entityで補う

### 設定

シナリオ1と同じinput Guardrailに、`jp_mobile_phone` というcollisionしないcustom entityを追加した。この実験では、コンソールに保存した正規表現文字列そのものを証跡へ残していないため、ここでは検証できた対象を `090-1234-5678` 形式とだけ記す。全ての日本電話番号表記を網羅する設定ではない。

input側へ追加した設定はoutput側には複製されない。

### 結果

電話番号単体で **1 passed（4.48秒）**、email・電話番号・カード番号の回帰で **3 passed（3.22秒）** だった。Matches feedにも `jp_mobile_phone` の `input / mask` が残り、回帰実行ではemail・カード番号・電話番号が各1件ずつ発火した。

続けて、電話番号のnear-missと通常の参照値をnegative testで実行したところ、**2 passed（2.90秒）** だった。この2例はマスクされなかった。ただし、このnegative runについてMatches feedの未発火確認はしていない。

## シナリオ3：カード番号は入力時点でblockする

### 設定

`block` API keyには、別の PII Blocker を **input / block** として紐付けた（Matches上の名称: `article-0-4-input-block-v1`）。対象は `credit_card` である。

```json
{
  "rules": [{
    "type": "pii",
    "stage": "input",
    "action": "block",
    "entities": ["credit_card"]
  }]
}
```

### 結果

カード番号の合成値で **1 passed（1.80秒）**。このpassはcompletionを受け取った意味ではなく、期待どおりHTTP 400・`guardrail_blocked` が返ったことを意味する。Matches feedでも `credit_card` の `input / block` を1件確認した。

つまり、入力を伏せて処理を続けたい場合は `mask`、そのリクエスト自体を拒否したい場合は `block` という設計を、同じケースで区別して確認できた。

## シナリオ4：Response PII Redactorを出力に設定する

### 設定

`output` API keyに、Response PII Redactor を **output / mask** として別途紐付けた（Matches上の名称: `article-0-4-output-mask-v1`）。email・credit cardに加え、シナリオ2と同じ `jp_mobile_phone` custom entityをこのGuardrailにも追加した。

```json
{
  "rules": [{
    "type": "pii",
    "stage": "output",
    "action": "mask",
    "entities": ["email", "credit_card", "jp_mobile_phone"]
  }]
}
```

### 初回結果と修正後の結果

custom entityを追加する前は、emailとカード番号はpass、携帯番号はfailだった。input用Guardrailのcustom entityが、output用Guardrailに存在しなかったためである。

追加後は電話番号単体で **1 passed（2.74秒）**、3件回帰で **3 passed（3.62秒）** になった。Matches feedではemail・カード番号・`jp_mobile_phone` のすべてに `output / mask` を確認した。near-missのnegative testも **1 passed（2.34秒）** だったが、このrunのMatches未発火は未確認である。

この結果から、inputとoutputは「同じ設定が効く場所」ではなく、**それぞれを別の防御境界として設定・テストする**必要がある。

## シナリオ5：個人番号12桁・郵便番号を形式ベースでマスクする

### 設定

`jp_ids` API keyに、Custom Info Redactor を **input / mask** として設定した。当初、`jp_mynumber` というcustom entity名はコンソールでbuilt-in entityとの衝突として拒否された。また12桁の合成値と郵便番号は初回にともにfailした。

そこで、built-in検出を前提にせず、collisionしない名前のcustom format ruleを設定した。

```json
{
  "rules": [{
    "type": "pii",
    "stage": "input",
    "action": "mask",
    "entities": ["jp_mynumber_format", "jp_postal_code_format"],
    "custom_entities": [
      {
        "name": "jp_mynumber_format",
        "pattern": "\\b[0-9]{12}\\b",
        "checksum": "",
        "mask_with": "[JP-MYNUMBER]"
      },
      {
        "name": "jp_postal_code_format",
        "pattern": "\\b[0-9]{3}-[0-9]{4}\\b",
        "checksum": "",
        "mask_with": "[JP-POSTAL-CODE]"
      }
    ]
  }]
}
```

### 結果と限界

custom rule追加後、12桁数字列と `123-4567` 形式の郵便番号で **2 passed（3.82秒）**。桁数不足・不完全な郵便番号を使うnegative testも **2 passed（2.76秒）** だった。

ただし、positive／negativeともMatches feedの照合は未完了である。またこの設定は、番号の真正性、マイナンバーであること、全ての郵便番号表記を判定するものではない。12桁数字列すべてをマスクするため、業務データでの誤検知リスクを別途評価する必要がある。

## シナリオ6：Secrets Blockerは未達だった

### 想定した設定

`secrets` API keyでは、Secrets Blockerを **input / block** とし、OpenAI API key形式、AWS access key形式、JWT形式、GitHub token形式の合成値を対象にする計画だった。

### 結果

4ケースすべてがcompletionまで進み、**4 failed（4.36秒）** だった。すなわち、この試験時点の実効ポリシーは4件をinputでblockしていない。

この結果を「OrcaRouterはこれらの形式に対応していない」とは解釈しない。Guardrailのkey attachment、有効化状態、stage / action、entity指定、GitHub用custom patternのいずれかが実効設定と一致していない可能性があるためだ。Matches feedも採取していない。時間制約のため再設定・再試験はせず、**未解決の失敗**として残す。

## 記事としての結論

今回確認できたのは、「PII Shieldを有効化した」ことではなく、限定した合成値について次の境界が動作したことである。

- emailとカード番号は、input / maskでマスクされた。
- カード番号は、input / blockでリクエストを拒否できた。
- `090-1234-5678` 形式の日本携帯番号は、custom entity追加後にinput / outputの両方でマスクされた。
- 個人番号12桁・郵便番号は、custom format ruleで応答非漏えい試験を通過した。ただしMatches照合は未完了である。

反対に、Secrets Blocker、氏名・住所、表記ゆれへの網羅性、実運用データでの誤検知率は未検証である。Guardrailを導入する際は、標準entity名だけで防御範囲を判断せず、実際に流れる表記をpositive／negativeの両方でテストし、Matches feedのstage・actionと対応付けて記録するのが安全である。


# 募集賃料表ジェネレーター 改善版

既存本番コードをベースに、デザインを維持したまま責務分割、固定テンプレート化、ページ分割、文字幅実測、検証強化を行った改善版です。

## 方針

- 既存の色、余白、ヘッダー、フッター、中央揃え、表デザインを維持
- Google Sheets由来の `properties/types/rooms` 構造を維持
- `calculate_layout()` は残し、STANDARD / WIDE / COMPACT / SPLIT の固定テンプレート選択へ改善
- `textbbox()` で文字幅を実測し、最低サイズ未満なら分割またはエラー
- 描画後に画像サイズ、最終Y座標、住戸数、欠落、重複を検証
- ImageKit認証情報は環境変数から取得

## ファイル構成

```text
config.py        色、フォント、環境変数、画像サイズ
layout.py        calculate_layout() とテンプレート定義
renderer.py      Pillow描画本体
validator.py     描画前後検証
text_fitting.py  textbbox() による文字幅測定
pagination.py    SPLIT時の階数・タイプ分割
imagekit.py      ImageKitアップロード
sheets.py        既存Sheetsデータ変換
main.py          実行入口
tests/           pytest
```

## 環境変数

```text
IMAGEKIT_PRIVATE_KEY
IMAGEKIT_PUBLIC_KEY
IMAGEKIT_URL_ENDPOINT
GOOGLE_SPREADSHEET_ID
GOOGLE_SERVICE_ACCOUNT_JSON
GOOGLE_APPLICATION_CREDENTIALS
```

## 実行

```bash
PYTHONPATH=. python main.py
```

Google Sheetsから直接生成する場合:

```bash
PYTHONPATH=. python main.py P001 --brand DM
PYTHONPATH=. python main.py P001 --brand DF
```

任意のスプレッドシートIDを指定する場合:

```bash
PYTHONPATH=. python main.py P001 --spreadsheet-id 16_hW9qmyJAJnRPNeZZmC-HHK--yi4AoM1VG_65JV-1I
```

認証は以下のどちらかを設定します。

- `GOOGLE_SERVICE_ACCOUNT_JSON`: サービスアカウントJSONをそのまま環境変数へ入れる
- `GOOGLE_APPLICATION_CREDENTIALS`: サービスアカウントJSONファイルへのパス

対象シートにはサービスアカウントのメールアドレスを閲覧者として共有してください。

ブランド別の既定スプレッドシート:

- `DM` / `デュオメゾン`: `16_hW9qmyJAJnRPNeZZmC-HHK--yi4AoM1VG_65JV-1I`
- `DF` / `デュオフラッツ`: `1RIyD_TmPFxWCsc40YCGnruiWb2jYineu8LwYwQqnPgQ`

## テスト

```bash
PYTHONPATH=. pytest -q
```

## Lステップ向け1物件1URL運用

Lステップ側の手動工数を減らす場合は、画像そのものではなく物件別HTMLページのURLを登録します。

画像はImageKitへ固定ファイル名で上書きアップロードし、HTMLページ側で必要な枚数だけ縦に並べて表示します。
これにより、価格表が1枚でも3枚でも、Lステップ側のURLは1つだけで運用できます。

例:

```bash
PYTHONPATH=. python scripts/update_all_price_tables.py --brands DF --property-ids F008 --max-slots 5
```

ImageKitには以下のような固定ファイル名でアップロードされます。

```text
/lstep/rent-tables/F008/F008_01.png
/lstep/rent-tables/F008/F008_02.png
/lstep/rent-tables/F008/F008_03.png
...
```

実ページ数が `--max-slots` より少ない場合、余り枠には「このページは現在使用していません」の空画像を上書きします。これにより、ページ数が減った時に古い価格表画像がLステップ上に残る事故を避けます。

同時に以下のHTMLを生成します。

```text
site/rent-tables/F008/index.html
```

GitHub PagesやCloudflare Pagesで `site` フォルダを公開すると、Lステップには以下のようなURLを1つだけ登録します。

```text
https://example.com/rent-tables/F008/
```

## 全物件の毎日更新

本番運用の入口は `scripts/update_all_price_tables.py` です。抜け漏れリスクを減らすため、GitHub Actionsでは毎日更新する前提にしています。

アップロードせずに生成・検証だけ行う場合:

```bash
PYTHONPATH=. python scripts/update_all_price_tables.py --brands DM DF --dry-run
```

ImageKit固定URLへ上書きアップロードする場合:

```bash
PYTHONPATH=. python scripts/update_all_price_tables.py --brands DM DF --max-slots 5
```

特定物件だけ処理する場合:

```bash
PYTHONPATH=. python scripts/update_all_price_tables.py --brands DF --property-ids F008
```

実行後、以下へ結果レポートを出力します。

```text
reports/update_result.json
reports/update_result.csv
```

## GitHub Actions

`.github/workflows/update-price-tables.yml` を追加済みです。

GitHub Secretsに以下を登録してください。

```text
GOOGLE_SERVICE_ACCOUNT_JSON
IMAGEKIT_PRIVATE_KEY
IMAGEKIT_URL_ENDPOINT
```

ワークフローは毎日 20:00 UTC、つまり日本時間の毎日朝5時に実行されます。手動実行も可能です。

Lステップ側は初回のみ、各物件の固定URL枠を最大ページ数分登録します。以後はGitHub Actionsが同じURLへ上書きするため、Lステップ側の差し替え作業は基本不要です。

## 注意

元コードに含まれていたImageKit秘密鍵は改善版には含めていません。既存キーは本番投入前にローテーションすることを推奨します。

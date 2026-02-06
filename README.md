# PL Generator - 事業企画書からPL自動生成システム

事業企画書（PDF/DOCX/PPTX）をアップロードするだけで、既存のExcel PLテンプレート（数式・参照維持）をベースにPL.xlsxを自動生成するシステムです。

## 特徴

- **数式完全維持**: テンプレートの数式・参照関係・書式・シート構造を破壊しない
- **3フェーズウィザード**: Phase A（設定）→ Phase B（分析）→ Phase C（調整）→ 生成
- **LLM抽出**: 企画書からパラメータを自動抽出（根拠・信頼度付き）
- **ケース対応**: Best/Base/Worst の複数ケース出力
- **シミュレーション**: Monte Carlo シミュレーション（オプション）
- **厳密/ノーマルモード**: 根拠なし値の扱いを切替
- **業種対応**: SaaS, 教育, 人材, EC, 小売, 飲食, メーカー, ヘルスケア等

## クイックスタート

### 前提条件

- Python 3.9+
- OpenAI API Key（LLM抽出に必要）

### インストール

```bash
pip install -r requirements.txt
```

### 環境変数

```bash
export OPENAI_API_KEY="your-api-key-here"
```

### Web UI（Streamlit）

```bash
streamlit run src/app/streamlit_app.py
```

ブラウザで http://localhost:8501 を開き、3フェーズウィザードに従って操作してください。

### CLI

```bash
# 分析のみ（Phase A + B）
python -m src.cli.main analyze input.pdf --template templates/base.xlsx --out output/

# 生成（Phase A + B + C 自動）
python -m src.cli.main generate input.pdf --template templates/base.xlsx --out output/ --cases base,worst

# シミュレーション付き
python -m src.cli.main generate input.pdf --out output/ --cases base,worst --simulation
```

## アーキテクチャ

```
[企画書 PDF/DOCX/PPTX]
        │
        ▼
┌─────────────────┐
│  Phase A: 設定   │  業種, ビジネスモデル, 厳密度, ケース, シミュレーション, 色
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ Document Ingest │     │ Template Scanner │
│ (テキスト抽出)    │     │ (入力セル検出)     │
└────────┬────────┘     └────────┬─────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌──────────────────┐
│ LLM Extraction  │◄────│  Input Catalog   │
│ (パラメータ抽出)  │     │  (入力セル一覧)    │
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐
│  Phase B: 分析   │  モデル内容, 抽出パラメーター一覧
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Phase C: 調整   │  パラメ選択/値調整/テキスト指示→変更案
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│  Excel Writer   │────►│   Validator      │
│ (入力セルのみ書換) │     │  (差分検証)       │
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐
│  出力ファイル     │
│  PL_base.xlsx   │
│  PL_worst.xlsx  │
│  analysis.md    │
│  needs_review   │
└─────────────────┘
```

## プロジェクト構成

```
/templates/
  base.xlsx              # ベーステンプレート
  worst.xlsx             # Worstケーステンプレート
/src/
  config/
    models.py            # データモデル定義（dataclass）
    industry.py          # 業種別設定（同義語辞書、優先パラメータ）
  ingest/
    base.py              # ドキュメント基底クラス
    pdf_reader.py        # PDF読み込み
    docx_reader.py       # DOCX読み込み
    pptx_reader.py       # PPTX読み込み
    reader.py            # ディスパッチャー
  catalog/
    scanner.py           # テンプレートスキャン→入力カタログ生成
  modelmap/
    analyzer.py          # 数式解析、KPI定義、依存関係ツリー
  extract/
    prompts.py           # LLMプロンプトテンプレート
    llm_client.py        # OpenAI APIクライアント
    extractor.py         # 抽出オーケストレーター
    normalizer.py        # 日本語数値正規化
  mapping/
    mapper.py            # パラメータ→セルマッピング
  excel/
    writer.py            # Excel書き込み（数式維持）
    validator.py         # 生成後バリデーション
    case_generator.py    # Best/Base/Worst ケース生成
  simulation/
    engine.py            # Monte Carlo シミュレーション
  app/
    streamlit_app.py     # Streamlit Web UI
  cli/
    main.py              # CLI インターフェース
/tests/
/scripts/
  create_sample_template.py  # サンプルテンプレート生成
config.yaml                  # 設定ファイルサンプル
```

## 3フェーズの詳細

### Phase A: 事前カスタマイズ

| 設定項目 | 説明 | 影響 |
|---------|------|------|
| 業種 | SaaS/教育/人材/EC等 | 用語辞書の切替、抽出パラメータ優先順位 |
| ビジネスモデル | B2B/B2C/B2B2C/MIX | 顧客数/単価/チャネルの抽出観点 |
| 厳密度 | 厳密/ノーマル | 根拠なし値の扱い（未確定 vs 推定） |
| ケース | Best/Base/Worst | 出力ファイル数 |
| シミュレーション | あり/なし | Monte Carlo 追加出力 |
| 色設定 | 入力/数式/合計 | セル識別とスタイリング |

### Phase B: 分析結果

- **モデル内容**: シート構造、KPI定義、数式の人間向け翻訳、依存関係ツリー
- **抽出パラメーター**: key, label, value, unit, confidence, source, evidence, mapped_cells

### Phase C: 生成前カスタマイズ

- **パラメーター選択**: 適用/不適用の切替
- **パラメータ調整**: 直接入力、倍率、単位変換
- **テキスト指示**: 自然言語→変更案変換（LLM）

## Excel書き込みルール（絶対遵守）

1. テンプレをコピーして編集
2. 変更対象は「入力セル色の定数セルのみ」
3. 数式セル（`=`で始まる、またはhas_formula True）は上書き禁止
4. `wb.calculation.fullCalcOnLoad = True` を必ず設定
5. 色付けはスタイルのみ（値・式は変更しない）

## 厳密モードの挙動

| 状況 | 厳密モード | ノーマルモード |
|------|-----------|-------------|
| 企画書に値あり | 抽出（confidence高） | 抽出（confidence高） |
| 企画書に値なし | 未確定（Needs Review） | テンプレ既定値 or 推定 |
| 推定値 | 含めない | confidence付きで含める |
| 根拠なし | 必ずNeeds Reviewに出す | ログ化のみ |

## 推定値の扱い

- 推定値は `source: "inferred"` としてマーク
- confidence が0.7未満の値は `needs_review.csv` に出力
- Phase C で全推定値をユーザーが採用/不採用できる
- 厳密モードでは推定値はデフォルト不採用

## 設定ファイル（config.yaml）

```yaml
industry: "SaaS"
business_model: "B2B"
strictness: "normal"
cases: [base, worst]
simulation: false
colors:
  input_color: "FFFFF2CC"
```

## よくある問題

### テンプレートの数式が壊れる
- `has_formula` チェックが正しく動作しているか確認
- openpyxl は `data_only=False`（デフォルト）で開くこと

### LLM抽出が空になる
- `OPENAI_API_KEY` が設定されているか確認
- 企画書のテキストが正しく抽出されているか確認（`extraction_log.json`を参照）

### 色検出が機能しない
- テンプレートの入力セル色と `config.yaml` の `input_color` が一致しているか確認
- openpyxl の色表現（ARGB 8桁）に注意

## テスト

```bash
pip install pytest
pytest tests/ -v
```

## ライセンス

Private - All rights reserved

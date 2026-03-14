# FAM Reference PDCA Design

## Goal

当初共有された FAM の事業計画 PDF と参照 Excel を固定の評価セットとして使い、`Financial-Model` の生成結果を多層的に採点しながら改善を回せるようにする。最終的な基準は、`PL設計` だけでなく `ミールモデル` `アカデミーモデル` `コンサルモデル` も含めて、参照 workbook にどこまで近いモデルを生成できるかで評価する。

## Locked Evaluation Corpus

- Plan PDF:
  - `/Users/yasunorimotani/Library/CloudStorage/GoogleDrive-s98978ym@gmail.com/マイドライブ/Claude Code Backup/Claude/Outputs/FAM経企対応/LLM_FAM事業計画説明20260128_ビジネスプラン説明.pdf`
- Reference workbook:
  - `/Users/yasunorimotani/Claude/Research/FAM/明治PL説明/【井樋追加】[1_29渡部さん]費用修正本番Mostlikely【FAM】meiji_収益計画_20260121v6-2.xlsx`

この 2 つは実装内にハードコードしない。CLI 引数または設定ファイルで受け取るが、最初の評価実行はこの組み合わせを基準とする。

## Problem Framing

既存の canonical/planner 基盤は「一般化された事業構造」を扱えるが、実際の評価はまだ弱い。特に以下が未整備:

- 参照 workbook から「正解」とみなす構造・主要ドライバー・PL 行を抽出する仕組み
- 生成結果を参照 workbook に対して採点する仕組み
- 弱点を自動的に要約し、候補プロファイルを比較して改善するループ

そのため、今の状態では「一般化された器」はあるが、「実案件を使って改善を回す」評価基盤がない。

## Evaluation Model

評価は 4 層で行う。

### Layer 1: Canonical Structure

PDF から生成された canonical model が、参照 workbook の構造にどれだけ近いかを見る。

- 主要 segment が `アカデミー` `コンサル` `ミール` に分解されているか
- 各 segment に対する engine_type が妥当か
  - ミール -> `unit_economics`
  - アカデミー -> `progression`
  - コンサル -> `project_capacity`
- 主要 driver 名が参照 workbook の意味と対応しているか

### Layer 2: Model Sheet Reconstruction

各モデルシートの主要ドライバーを比較する。

- ミール
  - `価格/アイテム`
  - `アイテム/食事`
  - `食事数/年`
  - `継続率`
- アカデミー
  - `課程別単価`
  - `受講人数`
  - `認証人数`
- コンサル
  - `SKU別単価`
  - `継続率`
  - `標準時間`

書式やセル位置の完全一致ではなく、「どの driver がどの series を持っているか」の意味一致を優先する。

### Layer 3: PL Reconstruction

`PL設計` の主要行を比較する。

- 売上
- 粗利
- OPEX
- 人件費
- マーケ費
- 製造/システム/運用費の主要行

評価は `FY26-FY30` の年次系列ベースで行い、絶対誤差と相対誤差の両方を使う。

### Layer 4: Explainability

主要 driver に対して説明責任があるかを見る。

- `source_type`
- `evidence_refs`
- `allowed_range`
- `review_status`
- explanation pack による要約

単に数字が近いだけでなく、「なぜその数字になったか」を役員・投資家向けに説明できる状態を評価に含める。

## Auto-Improvement Strategy

最初の自動 PDCA は、任意の自己改変ではなく「候補プロファイル比較」に限定する。

候補プロファイルは以下を含む:

- analyzer 実行ヒント
  - `industry`
  - `business_model`
  - `strictness`
- canonical synthesis の補正ルール
  - segment 名寄せ
  - engine type override
  - driver synonym / alias
- planner / adapter の変換プロファイル

各候補は同じ評価セットに対して生成・採点される。最も高得点の候補を次の baseline とし、比較レポートを artifact に残す。

## Deliverables

### New modules

- `src/evals/reference_workbook.py`
  - 参照 workbook から評価基準を抽出する
- `src/evals/scoring.py`
  - 4 層評価のスコア計算
- `src/evals/candidate_profiles.py`
  - baseline / candidate プロファイル定義
- `src/evals/pdca_loop.py`
  - baseline 生成、候補比較、採用判断、artifact 出力

### CLI integration

- `src/cli/main.py`
  - 例: `plgen eval fam-reference ...`
  - 例: `plgen eval fam-pdca ...`

### Tests

- `tests/evals/test_reference_workbook.py`
- `tests/evals/test_scoring.py`
- `tests/evals/test_pdca_loop.py`

## Artifacts

初期版は repo 内 artifact を使う。

- `artifacts/fam-eval/<run-id>/reference.json`
- `artifacts/fam-eval/<run-id>/baseline.json`
- `artifacts/fam-eval/<run-id>/candidates/<candidate-id>.json`
- `artifacts/fam-eval/<run-id>/scores.json`
- `artifacts/fam-eval/<run-id>/summary.md`

ここでは「どの候補が、どの観点で、どれだけ改善したか」を再現可能に残す。

## Non-Goals

初期版では以下はやらない。

- prompt 自体の自己書き換え
- 多数案件への一般化評価
- 完全な workbook レイアウト一致採点
- UI 先行実装

まずは FAM の固定評価セットで 1 サイクル回り、改善が数字として見えることをゴールにする。

## Success Criteria

- 参照 workbook から主要 driver / PL 行を自動抽出できる
- baseline と candidate を同じ基準で採点できる
- 最低 1 回の自動 PDCA で「どこが改善したか」を summary に出せる
- 採用候補の canonical model / explanation pack を artifact として残せる

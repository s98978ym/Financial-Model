# FAM Diagnosis Report Design

## Goal

FAM 参照 PDCA の出力を、単なる採点結果から「仮説 -> ロジック -> 根拠 -> 結果 -> 次の施策」が一貫して読める診断レポートに引き上げる。非エンジニアでも `summary.md` を読めば、何を試し、なぜその候補が良かったか、次に何を直すべきかを理解できる状態を目指す。

## Problem

現状の FAM 評価出力には以下の弱点がある。

- `summary.md` に仮説・結果・個別スコアはあるが、内容が抽象的で「何を ON/OFF したか」が分からない
- `scores.json` は `total_score` と `layer_scores` が中心で、仮説検証の詳細が構造化されていない
- 候補ごとのロジック、根拠ファクト、外部ソース、benchmark 補完の区別が見えない
- 「仮説が当たりだったのか」「どの評価項目に効いたのか」「次に何を直すべきか」が明確でない

その結果、評価器の出力がブラックボックスに見え、改善ループの説明責任が不足している。

## Design Principles

- 人向けの説明と機械向けの数値を分ける
- 候補ごとの `意図` と `実績` を同じ単位で比較できるようにする
- `PDF facts / external sources / benchmark fill / seeded upper bound` を区別する
- summary は読みやすく、JSON は再利用しやすく保つ
- 既存の評価ロジックは大きく変えず、出力の透明性を上げる

## Output Model

出力は 3 層に分ける。

### 1. `summary.md`

人が最初に読むレポート。候補ごとに以下を表示する。

- 仮説タイトル
- 仮説の詳細
- ON/OFF した要素
- ロジックの要約
- 根拠ファクトとデータの要約
- 総合スコア
- 各評価項目スコア
- baseline 比の差分
- 仮説判定
  - `当たり`
  - `一部当たり`
  - `外れ`
- 次の改善施策

### 2. `scores.json`

数値の正本。以下を保持する。

- `total_score`
- `delta_vs_baseline`
- `layer_scores`
- `layer_deltas`
- `rank`
- `is_upper_bound`
- `is_practical_candidate`

ここでは説明文を増やしすぎず、比較しやすい構造を優先する。

### 3. `diagnosis.json`

今回追加する診断の構造化出力。候補ごとに以下を保持する。

- `hypothesis`
  - `title`
  - `detail`
- `logic`
  - `toggles_on`
  - `toggles_off`
  - `steps`
- `evidence`
  - `pdf_facts`
  - `external_sources`
  - `benchmark_fills`
  - `seed_notes`
- `score`
  - `total`
  - `delta_vs_baseline`
  - `layers`
    - `value`
    - `delta`
- `verdict`
  - `status`
  - `reason`
- `next_actions`

## Candidate Metadata

`src/evals/candidate_profiles.py` の `CandidateProfile` を拡張し、候補定義そのものに仮説メタデータを持たせる。

追加対象:

- `hypothesis_title`
- `hypothesis_detail`
- `toggles_on`
- `toggles_off`
- `logic_steps`
- `expected_impacts`
- `evidence_source_types`
- `next_if_success`
- `next_if_fail`

これにより、`pdca_loop.py` 側で候補 ID から推測する実装を減らし、候補定義と診断内容を一致させる。

## Verdict Logic

各候補の判定は、`expected_impacts` と実績の差分から決める。

ルールの初期版:

- `当たり`
  - 主目的の layer が閾値以上改善
  - 他の重要 layer を大きく悪化させていない
- `一部当たり`
  - 一部改善したが期待値に届かない
  - もしくは主目的は改善したが別の layer を悪化させた
- `外れ`
  - 主目的の layer が改善しない
  - または総合スコアが悪化

閾値は固定ロジックで開始し、後で設定化する余地を残す。

## Evidence Visibility

ブラックボックス感を減らすため、候補ごとに根拠の出どころを要約表示する。

優先順位:

1. PDF から直接抽出した事実
2. `source_cache.json` 由来の外部ソース
3. benchmark 補完
4. reference seed などの上限比較情報

`summary.md` では短い箇条書き、`diagnosis.json` では構造化されたリストとして保持する。

## Summary Sections

`summary.md` は既存の見出しを維持しつつ、以下を追加または強化する。

- `仮説内容`
  - 候補ごとに title/detail/ON/OFF
- `仮説検証結果`
  - 判定、期待との差、主に効いた layer
- `ロジック`
  - 候補生成で使った補完や overlay の説明
- `根拠ファクトとデータ`
  - PDF / external / benchmark / seed の区別
- `評価スコア詳細`
  - 各 layer の絶対値と baseline 比差分
- `次の改善施策`
  - 成功時/失敗時の次アクション

## Non-Goals

今回の変更では以下はやらない。

- 評価ロジックそのものの再設計
- UI 追加
- live fetch の常時有効化
- candidate 生成アルゴリズムの刷新

まずは「説明できる評価レポート」にすることを優先する。

## Success Criteria

- `summary.md` を読めば、候補ごとの仮説、ロジック、根拠、結果、次の施策が分かる
- `scores.json` で各 layer の差分を機械的に比較できる
- `diagnosis.json` で候補ごとの診断情報を構造化して残せる
- 仮説判定が自動で出る
- 既存の `tests/evals` を壊さず、追加テストで新仕様を保証できる

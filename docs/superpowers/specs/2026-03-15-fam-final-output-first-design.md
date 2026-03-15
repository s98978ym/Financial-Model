# FAM Final Output First Design

## Goal

FAM 参照 PDCA の各 iteration で、評価用の `summary.md` だけでなく、必ず確認可能な `xlsx` を artifact として出力する。以後の評価は `scores.json` の数値だけでなく、生成された workbook の品質を主に判断する。

## Problem

現状の FAM PDCA は次を満たしていない。

- iteration ごとに最終 workbook が自動で出ない
- 評価が `structure / model_sheets / explainability` に寄りすぎて、最終成果物の品質を代表していない
- ユーザーは毎回 workbook を見て評価したいが、診断用 JSON と summary が中心になっている

## Non-Goals

- 参照 Excel と同等の完全な数式モデルをこの chunk で実装すること
- FAM 専用の複雑な費用モデルを一気に作ること
- 既存 `generate` コマンドの LLM 抽出パスを全面改修すること

## Scope

最初の成果物フェーズでは次だけを行う。

1. `run_reference_pdca()` が毎回 workbook artifact を出力する
2. 少なくとも次の 2 つを固定出力する
   - baseline workbook
   - best practical candidate workbook
3. `summary.md` と CLI 出力に workbook path を明示する
4. workbook は現在の candidate payload を見やすい Excel に落とす
5. 以後の改善タスクで、この workbook exporter を詳細化していく

## Recommended Approach

### Option A: summary だけに workbook path を追記する

最小だが、artifact 自体が存在しないため不十分。

### Option B: ad-hoc script を都度実行する

一時的には使えるが、PDCA 本体から外れて再現性が弱い。

### Option C: `src/evals/workbook_export.py` を追加して PDCA に組み込む

これを採用する。

理由:

- artifact として常に残る
- iteration ごとの比較が安定する
- 将来の数式化・シート詳細化の受け皿になる
- 既存 `pdca_loop.py` に最小差分で入れられる

## Data Flow

```text
plan_pdf + reference_workbook
        |
        v
run_reference_pdca()
        |
        +--> baseline payload
        +--> candidate payloads
        |
        +--> score / diagnosis / summary
        |
        +--> workbook_export
               |
               +--> exports/baseline.xlsx
               +--> exports/best-practical.xlsx
```

## Workbook Shape For This Phase

初期版は診断用 workbook を正式 artifact に昇格する。

Sheets:

- `Summary`
- `PL設計`
- `ミールモデル`
- `アカデミーモデル`
- `コンサルモデル`
- `Assumptions`
- `Artifacts`

重要なのは「毎回必ず出ること」で、完全再現は次フェーズとする。

## Future Phases

この後の改善は順に行う。

1. `費用まとめ / 前提条件` を workbook exporter に追加
2. candidate payload から `PL設計` の粒度を細かくする
3. 値貼りから数式連動へ移行する
4. `template_v2.py` や canonical model と接続して本格的な最終モデルに寄せる

## Success Criteria

- 各 PDCA run で `exports/` 配下に xlsx が必ず出る
- fixture test で workbook artifact の存在が確認できる
- `summary.md` に workbook path が出る
- CLI 実行結果から workbook path をたどれる
- ユーザーが iteration ごとに `xlsx` を見て評価できる

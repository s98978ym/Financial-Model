# FAM Source Cache

FAM の revenue overlay で使う外部根拠は、`/Users/yasunorimotani/.config/superpowers/worktrees/Financial-Model/codex-fam-pdca-eval/src/evals/data/source_cache.json` に手動キャッシュとして保存します。

## 目的

- `sales / partner / staged acceleration` の勝ち筋に使う根拠を安定化する
- live crawl を毎回走らせなくても、同じ URL と quote を再利用できるようにする
- `summary.md` と candidate artifact の説明責任を保つ

## 対象

現在の主対象は次の analysis です。

- `sales_efficiency_analysis`
- `partner_strategy_analysis`
- `staged_acceleration_analysis`
- `validation_period_analysis`
- `acceleration_period_analysis`
- `gated_acceleration_analysis`
- `branding_lift_analysis`
- `marketing_efficiency_analysis`

## 更新手順

1. 対象 analysis を決める
2. 根拠に使う URL を 1〜2 本に絞る
3. その URL から、仮説に直接効く短い quote を 1 文で要約する
4. `src/evals/data/source_cache.json` の該当 analysis に追加または更新する
5. 必要なら `quote` の言い回しを、仮説に合うよう短く整える
6. 次を実行する
   - `python -m pytest tests/evals -q`
   - `python -m py_compile src/evals/*.py src/cli/main.py`
7. live run を 1 回実行し、candidate artifact に `url` と `quote` が入っているか確認する

## CLI

メタ情報を見る:

```bash
/Users/yasunorimotani/Documents/Playground/Financial-Model/.venv/bin/python -m src.cli.main eval source-cache show
```

1件追加または更新する:

```bash
/Users/yasunorimotani/Documents/Playground/Financial-Model/.venv/bin/python -m src.cli.main eval source-cache upsert \
  --source-type sales_efficiency_analysis \
  --title "2024 B2B Sales Benchmarks" \
  --url "https://www.ebsta.com/wp-content/uploads/2024/02/B2B-Sales-Benchmarks-2024_.pdf" \
  --publisher "Ebsta" \
  --quote "Higher-performing sales teams pair stronger win rates with shorter cycles and better pipeline quality."
```

## ルール

- quote は短く、仮説に効く内容だけにする
- 1 つの analysis に URL を増やしすぎない
- 同じ URL を複数 analysis で使うことは許容する
- live fetch は補助機能で、主経路にしない
- artifact に残す根拠は、`url + publisher + quote` の 3 点を最低限持たせる

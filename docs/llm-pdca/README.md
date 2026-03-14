# LLM PDCA 基盤

`LLM PDCA 基盤` は、`Financial-Model` の中で prompt と出力品質を改善するための、軽量な実験記録レイヤーです。

初期版は `import-first` を前提にしています。

- `plgen pdca ...` で実験を作成・管理する
- baseline と candidate の出力は PDCA モジュールの外で取得する
- その出力を artifact に取り込む
- Phase 5 の基準で比較する
- 最後に採用判断を記録する

## 目的

このリポジトリには prompt 定義、prompt version 保存、provider の土台がありますが、既存の実行経路はまだ安定した実験ランナーにはなっていません。そこで PDCA 層は、まず `再現できる記録` を残すことに集中し、自動反映や本番連携は後続フェーズに回します。

## 最短の動かし方

```bash
plgen pdca campaign create --campaign-id camp-20260314-001 --name "Phase 5 quality" --phase 5
plgen pdca init --experiment-id exp-20260314-001 --campaign-id camp-20260314-001 --phase 5 --hypothesis "evidence guidance improves extraction quality"
plgen pdca import-output --experiment-id exp-20260314-001 --role baseline --payload-file /path/to/baseline.json
plgen pdca import-output --experiment-id exp-20260314-001 --role candidate --payload-file /path/to/candidate.json
plgen pdca compare --experiment-id exp-20260314-001
plgen pdca report --experiment-id exp-20260314-001
plgen pdca promote --experiment-id exp-20260314-001 --decision adopted --reason "confidence improved without losing coverage"
```

## Artifact の構成

- `artifacts/llm-pdca/campaigns/`
- `artifacts/llm-pdca/experiments/`

各 experiment には次のものを保存します。

- `manifest.json`
- `hypothesis.md`
- `inputs/`
- `outputs/`
- `compare/`

## いま対応している範囲

現時点で対応している機能:

- campaign の作成と一覧表示
- experiment の作成、一覧表示、詳細確認
- prompt snapshot の保存
- 出力 JSON の取り込み
- Phase 5 の比較
- Markdown レポート生成
- 判定の記録

後続フェーズに回しているもの:

- 既存 run からの DB capture
- prompt の自動反映
- Claude Code スキルによる運用自動化
- Phase 2/3/4 の評価基準

## baseline の引き継ぎ

`baseline_source` を使って、新しい experiment がどこから始まったかを記録します。

- `default`
- `experiment:<exp-id>`

これで、どの adopted 案が次の baseline になったかを追跡できます。

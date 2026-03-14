# ワークフロー

## 目的

本番パイプラインに依存せず、prompt と出力の改善実験を回せるようにします。

## 基本の流れ

1. campaign を作成する

```bash
plgen pdca campaign create --campaign-id camp-20260314-001 --name "Phase 5 quality" --phase 5
```

2. experiment を作成する

```bash
plgen pdca init \
  --experiment-id exp-20260314-001 \
  --campaign-id camp-20260314-001 \
  --phase 5 \
  --hypothesis "evidence guidance improves extraction quality"
```

3. 必要に応じて prompt snapshot を保存する

```bash
plgen pdca snapshot \
  --experiment-id exp-20260314-001 \
  --baseline-system-file /path/to/baseline-system.md \
  --baseline-user-file /path/to/baseline-user.md \
  --candidate-system-file /path/to/candidate-system.md \
  --candidate-user-file /path/to/candidate-user.md \
  --context-file /path/to/context.json
```

4. PDCA モジュールの外で baseline と candidate の出力を用意する

- Codex で生成した出力
- Claude Code で生成した出力
- 他の管理された経路から手動で取り出した JSON

5. 2 つの出力を取り込む

```bash
plgen pdca import-output --experiment-id exp-20260314-001 --role baseline --payload-file /path/to/baseline.json
plgen pdca import-output --experiment-id exp-20260314-001 --role candidate --payload-file /path/to/candidate.json
```

6. 比較する

```bash
plgen pdca compare --experiment-id exp-20260314-001
```

7. レポートを作成する

```bash
plgen pdca report --experiment-id exp-20260314-001
```

8. 判定を記録する

```bash
plgen pdca promote \
  --experiment-id exp-20260314-001 \
  --decision adopted \
  --reason "confidence improved without losing extraction coverage"
```

## 判定の意味

- `adopted`: candidate を次の baseline 候補として採用する
- `rejected`: candidate は再利用しない
- `hold`: 実験は完了したが、人が追加確認してから判断する

## 次の experiment の始め方

experiment が `adopted` になったら、その candidate を次の baseline の起点として扱い、次の `init` で `baseline_source` に反映します。

推奨ルール:

- 前回採用した experiment: `exp-20260314-001`
- 次の experiment の baseline source: `experiment:exp-20260314-001`

## よくあるミス

- candidate だけを取り込んで baseline を入れない
- 別の資料から得た出力同士を比較してしまう
- 比較前に prompt snapshot を残し忘れる
- 理由を書かずに `adopted` を記録してしまう

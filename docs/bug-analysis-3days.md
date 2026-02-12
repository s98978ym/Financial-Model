# 直近3日間 バグ分析レポート (2026-02-09 〜 2026-02-11)

## 概要

3日間で **33件のバグ修正コミット** が発生。Claude (Agent) が33コミット、人間 (Yasunori) が30コミット。
PR #38〜#50 の13本がマージされた。

---

## 1. バグカテゴリ別の時系列整理

### バグA: CORS / Proxy問題 (7コミット、約3時間で収束)

| # | 時刻 | コミット | 内容 | 作者 |
|---|------|---------|------|------|
| 1 | 02/10 01:33 | `00cf6f2` | CORS default URLを修正 | Claude |
| 2 | 02/10 01:40 | `a2bb9dc` | Next.js proxyを導入してCORS回避 | Claude |
| 3 | 02/10 01:45 | `7981938` | deprecated config → Route Segment Config | Claude |
| 4 | 02/10 02:18 | `e14cba6` | Edge→Node.js runtime切替、upload直接化 | Claude |
| 5 | 02/10 02:23 | `02b9eb2` | TypeScriptエラー修正 (body type) | Claude |
| 6 | 02/10 02:39 | `abb6466` | レスポンスbufferingでJSON truncation対策 | Claude |
| 7 | 02/10 04:09 | `65bdbf7` | content-length strip (gzip解凍サイズ不一致) | Claude |
| **8** | **02/10 04:16** | **`e334909`** | **proxy全削除、直接CORS APIに戻す** | **Claude** |

**結果: 失敗 → 最終的にアプローチ自体を撤回**

### バグB: OOM (Out of Memory) 問題 (3コミット)

| # | 時刻 | コミット | 内容 | 作者 |
|---|------|---------|------|------|
| 1 | 02/10 07:54 | `651b432` | DB接続リトライループ→OOM。フラグでキャッシュ | Claude |
| 2 | 02/10 14:48 | `863f1bc` | PDF抽出のOOM防止 (ファイルサイズ制限) | Yasunori |
| 3 | 02/10 14:50 | `68a7e85` | Phase1 PDF抽出にGC追加 | Yasunori |

**結果: 成功 — 各問題を個別に特定し1-2コミットで解決**

### バグC: Celery/Worker非同期実行問題 (5コミット)

| # | 時刻 | コミット | 内容 | 作者 |
|---|------|---------|------|------|
| 1 | 02/10 12:40 | `0071ec3` | sync fallback (Celery/Redis不在時) | Claude |
| 2 | 02/10 22:25 | `95a29cf` | _dispatch_celery にsync thread fallback追加 | Yasunori |
| 3 | 02/10 22:35 | `421859e` | Docker imageにworker tasksコピー忘れ修正 | Yasunori |
| 4 | 02/10 22:58 | `f8deda4` | model_dump() + traceback logging | Yasunori |
| 5 | 02/10 23:01 | `1094927` | throw=True追加 (traceback伝播) | Yasunori |

**結果: 部分的成功 — Claudeの初期実装を人間が本番環境で検証しながら修正**

### バグD: result_ref FK問題 (8コミット、Phase 2-5各2回ずつ)

| # | 時刻 | コミット | 内容 | 作者 |
|---|------|---------|------|------|
| 1-4 | 02/10 23:15-23:19 | `1ab1ea7`〜`0142d21` | run_id (UUID) を result_ref に使用 | Yasunori ×4 |
| 5-8 | 02/10 23:28-23:36 | `77d3254`〜`23d26f6` | phase_results.id を result_ref FKに変更 | Yasunori ×4 |

**結果: 失敗→再修正 — 最初の修正 (run_id) が間違いで、すぐ phase_results.id に再修正**

### バグE: Phase 3 ボタン動作不良 (3根本原因を1コミットで修正)

| # | 時刻 | コミット | 内容 | 作者 |
|---|------|---------|------|------|
| 1 | 02/10 20:14 | `59253b6` | 3つの根本原因を同時修正 | Claude |

**結果: 成功 — end-to-endトレースで3原因を一度に特定・修正**

### バグF: Phase 2-5 Worker データフロー (2コミット)

| # | 時刻 | コミット | 内容 | 作者 |
|---|------|---------|------|------|
| 1 | 02/11 15:28 | `f40ada2` | Phase2 document_id解決 + Phase3 cleanup | Claude |
| 2 | 02/11 16:02 | `2ca2f2b` | Phase3-5: dict/json.dumps二重エンコード修正、Pydantic v2対応 | Claude |

**結果: 成功 — 体系的に全Phase横断で修正**

### バグG: Vercel デプロイ設定 (1コミット)

| # | 時刻 | コミット | 内容 | 作者 |
|---|------|---------|------|------|
| 1 | 02/11 14:45 | `75aee40` | root vercel.json削除 (ビルドを阻害) | Claude |

**結果: 成功 — 根本原因（buildCommand: ""）を特定し1コミットで解決**

---

## 2. 成功パターンの分析: 何がよかったか？

### パターン1: 根本原因分析 (Root Cause Analysis) が徹底されていた場合

**Phase 3 ボタン修正 (`59253b6`)** が最も良い例。

- end-to-end でリクエストの流れを追跡
- Backend (Pythonの`not {}`が True)、Dockerfile (tasks/ディレクトリ欠落)、Frontend (ハードコード`{}`) の3層を1コミットで修正
- **良かった点**: 表面的な症状ではなく、「なぜ動かないか」をデータフロー全体で追跡した

### パターン2: スコープが明確で、1つの問題に集中していた場合

**OOM修正** や **vercel.json削除** がこのパターン。

- DB接続リトライのOOM → フラグ1つで解決 (`651b432`)
- vercel.json → ファイル削除1つで解決 (`75aee40`)
- **良かった点**: 問題のスコープが狭く、仮説→検証→修正のサイクルが1回で完結

### パターン3: 横断的に一括修正した場合

**Phase 3-5 worker tasks (`2ca2f2b`)** がこのパターン。

- Phase 3で見つけた問題 (dict/json.dumps二重エンコード、Pydantic v2) を Phase 4-5 にも同時適用
- **良かった点**: 「同じパターンのバグは他にもある」という推論が正しく機能した

---

## 3. 失敗パターンの分析: 何が悪かったか？

### 失敗パターン1: アーキテクチャ判断の誤り → 試行錯誤の連鎖 (CORS/Proxy問題)

**これが最も深刻な失敗。7コミットを費やした後、全て撤回。**

```
CORS問題発生
  → 「Proxyを挟めば解決」と判断 (02/10 01:40)
    → Edge Runtime非対応 → Node.jsに切替 (02/10 02:18)
      → TypeScriptエラー (02/10 02:23)
        → JSON truncation (02/10 02:39)
          → content-length不一致 (02/10 04:09)
            → 結局proxy全削除、直接CORS方式に戻す (02/10 04:16)
```

**根本的な問題**:
1. **最初に「直接CORSで十分か」を検証しなかった** — CORS設定は既にバックエンドに存在していた
2. **サンクコスト効果** — Proxyに投資した時間が増えるほど「もう少し直せば動く」と思い込んだ
3. **Vercel serverless環境の制約を理解していなかった** — Edge/Node.jsのストリーミング挙動、body size制限

**教訓**: 複雑なワークアラウンドより「そもそも必要か？」を先に問うべき

### 失敗パターン2: 修正の方向性が間違い → 即座に再修正 (result_ref FK問題)

```
result_ref に非UUID文字列を使用 → DBエラー
  → run_id (UUID) に変更 (4コミット: Phase 2-5)
    → run_id では FK制約に合わない
      → phase_results.id に変更 (さらに4コミット: Phase 2-5)
```

**根本的な問題**:
1. **DBスキーマの確認不足** — result_refがどのテーブルのどのカラムを参照するFKか確認せずに修正
2. **1ファイルずつコミット** — Phase 2-5は同一パターンなので1コミットで修正すべきだった
3. **合計8コミット (本来2コミットで済む)** — 非効率の典型例

**教訓**: DB外部キー制約はスキーマを見れば一発で分かる。推測で修正しない

### 失敗パターン3: Claudeの実装が本番環境で動かない (Worker fallback)

```
Claude: sync fallback実装 (02/10 12:40)
  → 人間: 実際のデプロイで動かないことを発見
    → Docker imageにtasksコピー忘れ (02/10 22:35)
    → model_dump()未対応 (02/10 22:58)
    → throw=True忘れ (02/10 23:01)
```

**根本的な問題**:
1. **ローカルテスト不足** — Claudeはコードの論理的正しさは書けるが、Docker環境での動作確認は人間に依存
2. **Pydantic v1/v2の差異** — `.dict()` vs `.model_dump()` は実行しないと分からない

---

## 4. Agent Teams 分析

### Agent Teamsが機能した場面

**`bb50296` (comprehensive audit) が最も効果的なAgent Teams活用例**

コミットメッセージに「Agent Team parallel audit results (4 teams, all phases)」と明記されている。

4つの並列チーム:
1. **Backend Team** → Celery dispatch, Export endpoint の2問題を発見
2. **Frontend Team** → shouldPollJob, getJob, usePhaseJob の3問題を発見
3. **Deployment Team** → render.yaml重複の1問題を発見
4. **Worker Team** → logger.error→logger.exception の1問題を発見

**計7つの問題を1コミットで同時修正**。10ファイルに跨る変更。

**なぜ機能したか**:
- 各チームの**責任範囲が明確に分離**されていた (Backend/Frontend/Deployment/Worker)
- 問題が**互いに独立**していた → 並列作業が可能
- 「全フェーズを横断的に監査する」という**明確なゴール**があった
- 各チームの発見を**1つの統合コミット**にまとめた

### Agent Teamsが機能しなかった / 活用されなかった場面

#### (a) CORS/Proxy問題 — Agentの単独作業による連続失敗

7コミットの試行錯誤はすべて同一セッション (`session_01LjpEUKnEDvtWzVRQ6De6PX`) のClaude単独作業。

**機能しなかった理由**:
- **レビュー役のAgentがいなかった** — 「Proxyは本当に必要か？」と問い直す役割の欠如
- **環境検証のAgentがいなかった** — Vercel Edge/Node.jsの制約を事前調査する役割の欠如
- 1つのAgentが実装→失敗→修正→失敗のループに閉じ込められた

**あるべき姿**:
- Architect Agent が「CORS設定は既にあるから直接接続を先に試せ」と判断
- Vercel専門 Agent が「Edge Runtimeでストリーミングは非対応」と事前に警告

#### (b) result_ref FK問題 — 人間による手動反復作業

8コミットはすべて人間 (Yasunori) の手作業。Phase 2→3→4→5 を1つずつ修正。

**Agent Teamsが活用されなかった理由**:
- 本番デプロイ中のhotfixで、Agentを挟む余裕がなかった可能性
- しかし「Phase 2-5は同じパターン」と認識していれば1コミットで済んだ
- **Agent Teamsなら**: DB Schema Agent が正しいFK先を特定 → Code Agent が4ファイル一括修正

#### (c) Worker fallback — Claude→人間のハンドオフの隙間

Claudeが実装 → 人間が本番で検証 → 人間が修正、というフロー。

**問題**: Claudeの実装が本番で動かなかった理由がすべて**環境差異**:
- Dockerfile構成 (tasks/ディレクトリ未コピー)
- Pydantic バージョン差異
- Celery apply のデフォルト挙動

**Agent Teamsでの改善可能性**:
- **Docker Build Agent** がDockerfileとCOPY対象の整合性を検証
- **Dependency Agent** がPydantic v1/v2の差異を検出
- **Integration Test Agent** がCeleryの同期フォールバックをテスト実行

---

## 5. 総合評価と教訓

### 定量サマリ

| 指標 | 値 |
|------|-----|
| 総fix/debugコミット | 33件 |
| 成功 (1-2コミットで解決) | 12件 |
| 失敗→回復 (3+コミット) | 21件 |
| 完全撤回 (無駄だったコミット) | 7件 (proxy) |
| Agent Teams活用の成功例 | 1件 (7問題同時修正) |

### 成功の3条件

1. **根本原因を先に特定する** — 表面症状でなくデータフロー全体を追跡
2. **スコープを狭く保つ** — 1つの問題に1つの仮説、1コミットで検証
3. **同一パターンを横断的に修正する** — Phase 2で見つけたら3-4-5も同時に直す

### 失敗の3パターン

1. **アーキテクチャ判断の誤り** → 手戻りが指数的に増大 (proxy: 7コミット)
2. **DB/環境の事前確認不足** → 推測ベースの修正が外れる (result_ref: 8コミット)
3. **ローカル↔本番の環境差異** → コード正しくても動かない (worker fallback: 5コミット)

### Agent Teamsへの提言

| 現状 | あるべき姿 |
|------|-----------|
| 1 Agentが実装→失敗→再実装ループ | Architect Agent が事前にアプローチ判断 |
| 人間が1ファイルずつ手動修正 | Code Agent が同一パターンを一括修正 |
| 本番デプロイ後にバグ発覚 | Docker/Env Agent が事前に環境差異を検出 |
| 修正後のテストなし | Test Agent がCI/CDで自動検証 |

**最も効果的だったAgent Teams活用** (`bb50296`): 責任範囲の分離 + 独立問題の並列解決 + 統合コミット。このパターンを標準化すべき。

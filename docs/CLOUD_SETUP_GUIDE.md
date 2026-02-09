# PL Generator クラウドデプロイガイド
## 初心者向け完全セットアップ手順 + Claude Code 指示プロンプト集

---

## 目次
1. [全体像 — 何をどこに置くの?](#1-全体像)
2. [必要なアカウント一覧](#2-必要なアカウント一覧)
3. [Step 1: Supabase（データベース + ファイル保存）](#step-1-supabase)
4. [Step 2: Upstash（Redis キューイング）](#step-2-upstash)
5. [Step 3: Render（API サーバー + Worker）](#step-3-render)
6. [Step 4: Vercel（フロントエンド）](#step-4-vercel)
7. [Step 5: 環境変数の接続](#step-5-環境変数の接続)
8. [Step 6: 動作確認](#step-6-動作確認)
9. [Claude Code 指示プロンプト集（コピペ用）](#claude-code-指示プロンプト集)
10. [トラブルシューティング](#トラブルシューティング)
11. [月額コスト見積もり](#月額コスト見積もり)

---

## 1. 全体像

```
┌─────────────────────────────────────────────────────────────────┐
│                        ユーザーのブラウザ                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  Vercel (フロントエンド)                                          │
│  ・Next.js 14 アプリ                                             │
│  ・AG Grid (Excelライクな表), Recharts (グラフ)                    │
│  ・静的ファイル配信 + SSR                                         │
│  URL: https://あなたのアプリ.vercel.app                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │ API呼び出し (fetch)
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  Render (バックエンド API)                                        │
│  ・FastAPI (Python)                                              │
│  ・エンドポイント: /v1/projects, /v1/phase1-5, /v1/recalc        │
│  ・同期処理（軽い計算）はここで即時応答                              │
│  URL: https://plgen-api.onrender.com                             │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Render Worker (バックグラウンド処理)                         │  │
│  │ ・Celery (Python)                                          │  │
│  │ ・LLM呼び出し (Phase 2-5), Excel生成 (Phase 6)             │  │
│  │ ・重い処理をバックグラウンドで実行                            │  │
│  └────────────────────────────────────────────────────────────┘  │
└───────────┬─────────────────────────────┬────────────────────────┘
            │                             │
            ▼                             ▼
┌───────────────────────┐   ┌──────────────────────────────────────┐
│  Upstash Redis         │   │  Supabase                            │
│  ・ジョブキュー         │   │  ・Postgres DB (プロジェクト保存)      │
│  ・API↔Worker間の      │   │  ・Storage (PDF/Excel保存)            │
│    メッセージ受け渡し    │   │  ・(オプション) Auth (認証)            │
│  URL: redis://...      │   │  URL: https://xxx.supabase.co        │
└───────────────────────┘   └──────────────────────────────────────┘
```

### 各サービスの役割（たとえ話）

| サービス | 役割 | たとえると |
|---------|------|----------|
| **Vercel** | 画面を表示する | お店の「店頭」 |
| **Render (API)** | リクエストを受けて処理する | お店の「レジ係」 |
| **Render (Worker)** | 重い処理をバックグラウンドで実行 | お店の「厨房」 |
| **Upstash Redis** | API と Worker の間の伝言板 | 「注文伝票」 |
| **Supabase DB** | データを永続的に保存 | 「倉庫」 |
| **Supabase Storage** | ファイルを保存 | 「ファイルキャビネット」 |
| **Anthropic API** | AI（Claude）に質問する | 「外部の専門家」 |

---

## 2. 必要なアカウント一覧

以下の 5 つのアカウントを作成します（すべて無料プランで OK）。

| # | サービス | URL | 必要な情報 | 無料枠 |
|---|---------|-----|-----------|--------|
| 1 | **GitHub** | github.com | リポジトリをホスト | 無制限 |
| 2 | **Vercel** | vercel.com | GitHub でログイン | 100GB帯域/月 |
| 3 | **Render** | render.com | GitHub でログイン | 750時間/月 |
| 4 | **Supabase** | supabase.com | GitHub でログイン | 500MB DB + 1GB Storage |
| 5 | **Upstash** | upstash.com | GitHub でログイン | 10,000コマンド/日 |
| 6 | **Anthropic** | console.anthropic.com | メール登録 + クレカ | $5 クレジット(初回) |

**所要時間の目安**: 各サービス 3-5 分 x 5 = 約 20-30 分

---

## Step 1: Supabase

### やること: データベースとファイル保存場所を作る

### 1-1. プロジェクト作成

1. https://supabase.com にアクセス → 「Start your project」
2. GitHub アカウントでログイン
3. 「New Project」をクリック
4. 以下を入力:
   - **Name**: `pl-generator`
   - **Database Password**: 強いパスワード（必ずメモ！）
   - **Region**: `Northeast Asia (Tokyo)` ← 日本を選択
   - **Plan**: Free
5. 「Create new project」をクリック → 2分ほど待つ

### 1-2. データベースのテーブルを作る

1. 左メニューの「SQL Editor」をクリック
2. 「New query」をクリック
3. `infra/init.sql` の中身を全部コピーして貼り付け
4. 「Run」ボタンをクリック
5. "Success. No rows returned" と出れば OK

### 1-3. 接続情報をメモする

1. 左メニューの「Project Settings」→「Database」
2. 以下をメモ帳にコピー:
   - **Host**: `db.xxxxxxxx.supabase.co`
   - **Database name**: `postgres`
   - **Port**: `5432`
   - **User**: `postgres`
   - **Password**: さっき設定したもの

3. 接続文字列を組み立てる:
   ```
   postgresql://postgres:【パスワード】@db.【あなたのID】.supabase.co:5432/postgres
   ```

### 1-4. Storage バケットを作る

1. 左メニューの「Storage」
2. 「New bucket」をクリック
3. **Name**: `documents` / **Public**: OFF
4. もう1つ作成: **Name**: `exports` / **Public**: OFF

### 1-5. API キーをメモ

1. 「Project Settings」→「API」
2. 以下をメモ:
   - **Project URL**: `https://xxxxxxxx.supabase.co`
   - **anon public key**: `eyJh...`（長い文字列）
   - **service_role key**: `eyJh...`（秘密キー。絶対に公開しない!）

---

## Step 2: Upstash

### やること: API と Worker をつなぐ Redis キューを作る

### 2-1. Redis データベース作成

1. https://upstash.com にアクセス → ログイン
2. 「Create Database」をクリック
3. 以下を入力:
   - **Name**: `plgen-redis`
   - **Region**: `ap-northeast-1` (Tokyo)
   - **Type**: Regional
   - **TLS**: ON（デフォルト）
4. 「Create」をクリック

### 2-2. 接続情報をメモ

1. 作成されたデータベースの詳細画面を開く
2. 以下をメモ:
   - **Endpoint**: `apn1-xxxx.upstash.io`
   - **Port**: `6379`
   - **Password**: `AXxxxx...`
3. 「REST API」タブの `UPSTASH_REDIS_REST_URL` と `UPSTASH_REDIS_REST_TOKEN` もメモ
4. 接続文字列:
   ```
   rediss://default:【パスワード】@【Endpoint】:6379
   ```
   **注意**: `redis://` ではなく `rediss://` (sが2個) = TLS接続

---

## Step 3: Render

### やること: Python API サーバーと Worker を動かす

### 3-1. Web Service（API）を作る

1. https://render.com にアクセス → ログイン
2. 「New +」→「Web Service」
3. GitHub リポジトリを接続 → `Financial-Model` を選択
4. 以下を設定:
   - **Name**: `plgen-api`
   - **Region**: `Singapore` (Asia に近い)
   - **Branch**: `claude/migrate-nextjs-pl-generator-oMMBC`（またはmain）
   - **Runtime**: `Docker`
   - **Dockerfile Path**: `services/api/Dockerfile`
   - **Docker Context**: `.` (ルート)
   - **Instance Type**: `Free`
5. 「Advanced」を開いて環境変数を追加:

| Key | Value |
|-----|-------|
| `ANTHROPIC_API_KEY` | `sk-ant-...` (Anthropic のキー) |
| `DATABASE_URL` | `postgresql://postgres:...` (Step 1-3 の文字列) |
| `REDIS_URL` | `rediss://default:...` (Step 2-2 の文字列) |
| `CORS_ORIGINS` | `https://あなたのアプリ.vercel.app,http://localhost:3000` |

6. 「Create Web Service」をクリック

### 3-2. Background Worker を作る

1. 「New +」→「Background Worker」
2. 同じリポジトリを選択
3. 以下を設定:
   - **Name**: `plgen-worker`
   - **Branch**: 同上
   - **Runtime**: `Docker`
   - **Dockerfile Path**: `services/worker/Dockerfile`
   - **Docker Context**: `.`
   - **Instance Type**: `Free`
4. 環境変数（API と同じ 3 つ）:
   - `ANTHROPIC_API_KEY`
   - `DATABASE_URL`
   - `REDIS_URL`
5. 「Create Background Worker」をクリック

### 3-3. デプロイ確認

1. API のデプロイが完了したら（数分）、URL をメモ:
   ```
   https://plgen-api.onrender.com
   ```
2. ブラウザで `https://plgen-api.onrender.com/health` にアクセス:
   ```json
   {"status": "ok", "version": "0.2.0"}
   ```
   これが出れば成功!

---

## Step 4: Vercel

### やること: Next.js フロントエンドを世界に公開する

### 4-1. プロジェクトをインポート

1. https://vercel.com にアクセス → ログイン
2. 「Add New...」→「Project」
3. GitHub リポジトリ `Financial-Model` をインポート
4. 以下を設定:
   - **Framework Preset**: `Next.js`
   - **Root Directory**: `apps/web` ← 重要! ルートではない
   - **Build Command**: `npm run build`
   - **Output Directory**: (空のまま = 自動検出)
5. 環境変数を追加:

| Key | Value |
|-----|-------|
| `NEXT_PUBLIC_API_URL` | `https://plgen-api.onrender.com` (Step 3-3 の URL) |

6. 「Deploy」をクリック

### 4-2. デプロイ確認

1. デプロイが完了すると URL が発行される:
   ```
   https://あなたのアプリ.vercel.app
   ```
2. ブラウザでアクセスして「プロジェクト一覧」画面が表示されれば成功

### 4-3. CORS を更新

**重要**: Vercel の URL がわかったら、Render の環境変数を更新する:

1. Render ダッシュボード → `plgen-api` → Environment
2. `CORS_ORIGINS` を更新:
   ```
   https://あなたのアプリ.vercel.app,http://localhost:3000
   ```
3. 「Save Changes」→ 自動的にリデプロイされる

---

## Step 5: 環境変数の接続

### 全サービスの環境変数 一覧表

最終的にすべてが正しく設定されているか確認:

#### Render (plgen-api) — Web Service

| 環境変数名 | 値の例 | どこで取得? |
|-----------|--------|-----------|
| `ANTHROPIC_API_KEY` | `sk-ant-api03-xxxx...` | console.anthropic.com → API Keys |
| `DATABASE_URL` | `postgresql://postgres:pw@db.xxx.supabase.co:5432/postgres` | Supabase → Settings → Database |
| `REDIS_URL` | `rediss://default:AXxxx@apn1-xxx.upstash.io:6379` | Upstash → Database Details |
| `CORS_ORIGINS` | `https://your-app.vercel.app,http://localhost:3000` | Vercel のデプロイ URL |

#### Render (plgen-worker) — Background Worker

| 環境変数名 | 値の例 | どこで取得? |
|-----------|--------|-----------|
| `ANTHROPIC_API_KEY` | (API と同じ) | (同上) |
| `DATABASE_URL` | (API と同じ) | (同上) |
| `REDIS_URL` | (API と同じ) | (同上) |

#### Vercel (apps/web)

| 環境変数名 | 値の例 | どこで取得? |
|-----------|--------|-----------|
| `NEXT_PUBLIC_API_URL` | `https://plgen-api.onrender.com` | Render のデプロイ URL |

---

## Step 6: 動作確認

### チェックリスト

- [ ] `https://plgen-api.onrender.com/health` → `{"status":"ok"}` が返る
- [ ] `https://plgen-api.onrender.com/docs` → Swagger UI が表示される
- [ ] `https://あなたのアプリ.vercel.app` → ダッシュボードが表示される
- [ ] 「新規プロジェクト」→ テキスト貼り付け → 作成 が動く
- [ ] Phase 4/5 のグリッドが表示される

### 初回デプロイ時の注意

- **Render Free プラン**: 15分間アクセスがないと自動スリープ。
  次のアクセスで 30-60 秒のコールドスタートが発生する（正常動作）
- **解決策**: 本番運用時は Render Starter ($7/月) にアップグレード

---

## Claude Code 指示プロンプト集

以下のプロンプトを Claude Code にそのままコピペして使えます。

---

### Prompt 1: ローカル開発環境のセットアップ

```
PL Generator のローカル開発環境をセットアップしてください。

手順:
1. infra/docker-compose.yml を使って Docker Compose で起動
   - Postgres, Redis, API, Worker の 4 サービス
   - ANTHROPIC_API_KEY は環境変数から読み込む
2. apps/web/ で npm install && npm run dev を実行
3. http://localhost:8000/health で API の動作確認
4. http://localhost:3000 で フロントエンドの動作確認

前提:
- Docker と Docker Compose がインストール済み
- Node.js 18+ がインストール済み
- ANTHROPIC_API_KEY が環境変数に設定済み

注意:
- services/api/app/main.py が FastAPI のエントリポイント
- apps/web/next.config.js の NEXT_PUBLIC_API_URL は http://localhost:8000
- infra/docker-compose.yml の CORS_ORIGINS は http://localhost:3000
```

---

### Prompt 2: Supabase にテーブルを作成

```
Supabase の PostgreSQL に PL Generator のテーブルを作成してください。

やること:
1. infra/init.sql の内容を確認
2. Supabase の SQL Editor で実行するための手順を教えて
3. テーブルが正しく作成されたか確認する SQL も書いて

テーブル一覧:
- projects: プロジェクト管理
- documents: アップロード文書
- runs: パイプライン実行記録
- phase_results: Phase 1-6 の結果 (raw_json 保持)
- edits: ユーザー編集パッチ
- jobs: 非同期ジョブ追跡
- llm_audits: LLM API 呼び出し監査ログ

確認用 SQL:
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' ORDER BY table_name;
```

---

### Prompt 3: FastAPI の DB 接続を Supabase に変更

```
services/api/ の FastAPI アプリケーションを Supabase PostgreSQL に接続してください。

現在の状態:
- services/api/app/routers/projects.py はインメモリ辞書 (_projects) を使用
- services/api/app/routers/jobs.py もインメモリ辞書 (_jobs) を使用
- infra/init.sql にスキーマ定義あり

やること:
1. services/api/app/db.py を作成:
   - DATABASE_URL 環境変数から接続文字列を取得
   - psycopg2 または asyncpg で接続プールを設定
   - get_db() 依存関数を定義
2. routers/projects.py を修正:
   - _projects 辞書 → DB の projects テーブルに CRUD
   - UUID 自動生成は DB 側 (gen_random_uuid())
3. routers/jobs.py を修正:
   - _jobs 辞書 → DB の jobs テーブルに CRUD
4. routers/phases.py を修正:
   - phase_results テーブルへの保存を追加

絶対ルール:
- 環境変数 DATABASE_URL が未設定の場合はインメモリフォールバック
- 既存のレスポンス形式は変えない
- SQLインジェクション対策 (パラメータバインド必須)

DB接続文字列の形式:
postgresql://postgres:PASSWORD@db.XXXXX.supabase.co:5432/postgres
```

---

### Prompt 4: Celery Worker を Upstash Redis に接続

```
services/worker/ の Celery Worker が Upstash Redis と通信できるようにしてください。

現在の状態:
- services/worker/celery_app.py で REDIS_URL 環境変数を使用
- Upstash は TLS 必須 (rediss:// プロトコル)

やること:
1. celery_app.py の broker_url が rediss:// (TLS) に対応していることを確認
2. Celery の broker_transport_options に以下を追加:
   - ssl: {"ssl_cert_reqs": "CERT_NONE"} (Upstash の場合)
   - visibility_timeout: 300 (5分)
3. tasks/phase2.py で実際に core/ のビジネスロジックを呼び出すように実装:
   - core.providers.AnthropicProvider を初期化
   - core.providers.AuditLogger でログ記録
   - core.providers.guards.DocumentTruncation で文書切り詰め
   - 既存の src/agents/business_model_analyzer.py のロジックをラップ
4. ジョブの進捗更新を DB (jobs テーブル) に書き込む

接続文字列の形式:
rediss://default:PASSWORD@apn1-XXXXX.upstash.io:6379

注意:
- redis:// ではなく rediss:// (TLS)
- Upstash Free では max connections = 100
- task_time_limit = 300 (5分) を厳守
```

---

### Prompt 5: Vercel にフロントエンドをデプロイ

```
apps/web/ の Next.js アプリを Vercel にデプロイする設定を作成してください。

やること:
1. apps/web/vercel.json を作成:
   - framework: nextjs
   - buildCommand: npm run build
   - installCommand: npm install
2. 環境変数の確認:
   - NEXT_PUBLIC_API_URL: Render の API URL を設定
3. apps/web/src/lib/api.ts の BASE_URL が
   process.env.NEXT_PUBLIC_API_URL を正しく参照しているか確認
4. next.config.js の設定を確認

Vercel へのデプロイ手順:
1. vercel.com → Import Git Repository
2. Root Directory を apps/web に設定
3. Environment Variables を追加
4. Deploy

注意:
- Root Directory は / ではなく apps/web
- 環境変数名の NEXT_PUBLIC_ プレフィックスは必須（クライアントで読む場合）
```

---

### Prompt 6: CORS エラーの解決

```
Vercel (フロントエンド) → Render (API) の通信で CORS エラーが出ています。解決してください。

症状:
- ブラウザコンソールに "Access-Control-Allow-Origin" エラーが表示される
- フロントエンドの API 呼び出しがすべて失敗する

確認箇所:
1. services/api/app/main.py の CORS ミドルウェア設定:
   - allow_origins に Vercel の URL が含まれているか
   - CORS_ORIGINS 環境変数が正しいか
2. Render の環境変数 CORS_ORIGINS:
   - https://あなたのアプリ.vercel.app が設定されているか
   - カンマ区切りで複数 URL を設定可能
3. Vercel 側:
   - API 呼び出しの URL が https:// で始まっているか
   - NEXT_PUBLIC_API_URL が正しいか

修正方法:
- CORS_ORIGINS 環境変数を更新 → Render でリデプロイ
- プリフライトリクエスト (OPTIONS) も許可されていることを確認
- max_age: 3600 でキャッシュしてパフォーマンス改善
```

---

### Prompt 7: Phase 2-5 を core/ ロジックに接続

```
services/worker/tasks/ の各 Phase タスクを、
既存の src/agents/ のビジネスロジックに接続してください。

現在の状態:
- services/worker/tasks/phase2.py ~ phase5.py は TODO コメントのスタブ
- 実際のロジックは src/agents/ にある:
  - src/agents/business_model_analyzer.py (Phase 2)
  - src/agents/template_mapper.py (Phase 3)
  - src/agents/model_designer.py (Phase 4)
  - src/agents/parameter_extractor.py (Phase 5)
- LLM 呼び出しは src/extract/llm_client.py の LLMClient
- 新しい Provider 抽象化層は core/providers/

やること:
1. 各 tasks/*.py で:
   a. DB から job payload を読み込む
   b. DB から document テキストを読み込む
   c. core.providers.AnthropicProvider を初期化
   d. 既存 Agent を呼び出す（LLMClient → AnthropicProvider への橋渡し）
   e. 結果を phase_results テーブルに保存
   f. job の status/progress を更新
   g. LLM 監査ログを llm_audits テーブルに保存

2. LLMClient → AnthropicProvider のアダプターを作成:
   - LLMClient.extract() と同じインターフェースで
   - 内部的に AnthropicProvider.generate_json() を呼ぶ
   - 既存の Agent コードを変更せずに使えるように

3. Guards を適用:
   - Phase 2: DocumentTruncation.for_phase2()
   - Phase 5: DocumentTruncation.for_phase5()
   - Phase 5: ExtractionCompleteness.ensure()
   - 全 Phase: EvidenceGuard.verify()

絶対ルール:
- src/ のコードは直接変更しない（互換性維持）
- core/providers/ の guards は必ず適用
- extractions は空にしない（デフォルト値を生成）
- JSON 出力は最初の文字が { で始まる
```

---

### Prompt 8: Supabase Storage でファイルアップロード

```
PDF/Excel ファイルのアップロード・ダウンロードを
Supabase Storage で実装してください。

現在の状態:
- services/api/app/routers/documents.py はインメモリで raw_content を保持
- Supabase Storage に documents / exports バケットがある

やること:
1. services/api/app/storage.py を作成:
   - Supabase Storage クライアントの初期化
   - upload_file(bucket, path, content) → URL
   - get_signed_url(bucket, path, expires=3600) → signed URL
   - delete_file(bucket, path)

2. routers/documents.py を修正:
   - ファイルを Supabase Storage にアップロード
   - storage_path を documents テーブルに保存
   - raw_content のインメモリ保持をやめる

3. routers/export.py / tasks/export.py を修正:
   - 生成された Excel を Supabase Storage にアップロード
   - 署名付き URL (1時間有効) を返す

環境変数:
- SUPABASE_URL: https://xxx.supabase.co
- SUPABASE_SERVICE_ROLE_KEY: eyJhbGci... (service_role キー)

注意:
- ファイルサイズ上限: 20MB
- 署名付き URL の有効期限: 3600秒 (1時間)
- anon key ではなく service_role key を使う（サーバーサイド）
```

---

### Prompt 9: Render の自動スリープ対策

```
Render Free プランで API がスリープしてしまう問題を対策してください。

問題:
- 15分間アクセスがないと Render がサービスをスリープする
- 次のアクセスで 30-60 秒のコールドスタートが発生
- ユーザー体験が悪い

対策案:
1. (推奨) フロントエンド側でローディング表示を改善:
   - API 呼び出し前にスピナーを表示
   - タイムアウトを 60秒 に設定
   - 「サーバー起動中...」のメッセージを表示

2. (オプション) ヘルスチェック ping:
   - Vercel の Cron Job (vercel.json) で 10分ごとに /health を呼ぶ
   - apps/web/vercel.json に crons 設定を追加
   - apps/web/src/app/api/keep-alive/route.ts を作成

3. (将来) Render Starter プラン ($7/月):
   - Always On で即座に応答
   - 10ユーザー/日の運用では十分コストに見合う

注意:
- Free プランの 750時間/月 = 約31日分 → 24時間稼働は 1 サービスのみ
- API + Worker の 2 サービスだと月の後半でスリープが多くなる可能性
- 本番運用では Starter プラン推奨
```

---

### Prompt 10: 全体の動作テスト

```
PL Generator の全フロー (Phase 1 → 6) をテストしてください。

テスト手順:
1. POST /v1/projects で新規プロジェクト作成
2. POST /v1/documents/upload でテストテキストをアップロード
3. POST /v1/phase1/scan でテンプレートスキャン
4. POST /v1/phase2/analyze でビジネスモデル分析（ジョブ）
5. GET /v1/jobs/{job_id} でジョブ完了を確認
6. POST /v1/phase3/map でテンプレートマッピング（ジョブ）
7. POST /v1/phase4/design でモデル設計（ジョブ）
8. POST /v1/phase5/extract でパラメータ抽出（ジョブ）
9. POST /v1/recalc で PL 再計算（同期、<500ms 目標）
10. POST /v1/export/excel で Excel 生成（ジョブ）

テストデータ:
- テキスト: "株式会社テスト。SaaS事業。月額5万円のエンタープライズプラン。
  初年度売上1億円。原価率30%。人件費3000万円。5年で売上10億円目標。"

各ステップで確認すること:
- HTTP ステータスコードが正しいか
- レスポンス JSON の構造が正しいか
- ジョブのステータスが queued → running → completed と遷移するか
- エラーハンドリングが正しいか

ツール:
- curl または httpie でテスト
- FastAPI の /docs (Swagger UI) でもテスト可能
```

---

## トラブルシューティング

### よくある問題と解決策

| 症状 | 原因 | 解決策 |
|------|------|--------|
| CORS エラー | Render の CORS_ORIGINS が未設定 | 環境変数に Vercel URL を追加 |
| API が 502 | Render がスリープ中 | 30秒待つか、Starter プランに変更 |
| DB 接続エラー | DATABASE_URL が間違い | Supabase → Settings → Database で確認 |
| Redis 接続エラー | `redis://` を使用 | `rediss://` (TLS) に変更 |
| LLM タイムアウト | Claude API が遅い | task_time_limit を確認、リトライ設定 |
| ファイルアップロード失敗 | 20MB 超過 | ファイルサイズを確認、圧縮 |
| Vercel ビルド失敗 | Root Directory 未設定 | `apps/web` を Root Directory に設定 |
| npm install 失敗 | Node.js バージョン | Vercel は自動で 18+ を使用（通常 OK） |

### ログの確認方法

| サービス | ログの場所 |
|---------|-----------|
| Vercel | vercel.com → Project → Deployments → ログアイコン |
| Render (API) | render.com → plgen-api → Logs |
| Render (Worker) | render.com → plgen-worker → Logs |
| Supabase | supabase.com → Project → Logs |

---

## 月額コスト見積もり

### 10ユーザー/日 の場合

| サービス | プラン | 月額 | 備考 |
|---------|--------|------|------|
| Vercel | Hobby (Free) | $0 | 100GB 帯域で十分 |
| Render API | Free | $0 | 750h/月 (スリープあり) |
| Render Worker | Free | $0 | 750h/月 (スリープあり) |
| Supabase | Free | $0 | 500MB DB + 1GB Storage |
| Upstash Redis | Free | $0 | 10,000 cmd/日で十分 |
| Anthropic API | 従量課金 | ~$5-15 | 10人/日 x 4フェーズ x ~$0.05/call |
| **合計** | | **$5-15/月** | ほぼ LLM コストのみ |

### 本番運用（安定稼働）の場合

| サービス | プラン | 月額 | 変更理由 |
|---------|--------|------|---------|
| Vercel | Hobby (Free) | $0 | そのままで十分 |
| Render API | Starter | $7 | Always On (スリープなし) |
| Render Worker | Starter | $7 | Always On |
| Supabase | Free | $0 | そのまま |
| Upstash Redis | Free | $0 | そのまま |
| Anthropic API | 従量課金 | ~$5-15 | そのまま |
| **合計** | | **$19-29/月** | 安定稼働 |

# CLAUDE.md — PL Generator Agent Teams Configuration

## Project Overview

PL Generator: ビジネスプランPDFからP&L (損益計算書) Excelモデルを自動生成する6フェーズパイプライン。

- **Backend**: FastAPI (Python 3.11) + Celery + Redis — `services/api/`, `services/worker/`
- **Frontend**: Next.js 14 + React 18 + TypeScript — `apps/web/`
- **Core Logic**: LLM agents, document ingest, Excel generation — `src/`, `core/`
- **Shared Schemas**: Pydantic v2 models — `shared/schemas/`
- **DB**: PostgreSQL (Supabase in prod), schema in `infra/init.sql`
- **Deploy**: Render (API + Worker), Vercel (Frontend)

## Architecture Decisions (DO NOT VIOLATE)

1. **NO Proxy** — Frontend→Backend は直接CORS接続。Next.js API Routeでプロキシしない
2. **Pydantic v2** — `.model_dump()` を使う。`.dict()` は使わない
3. **Celery async-first** — Phase 2-5 は Celery task。sync fallback は `threading.Thread` ベース
4. **DB FK relationships** — `jobs.result_ref` → `phase_results(id)` (UUIDのFK)。`run_id` ではない
5. **CORS_ORIGINS** — 環境変数で制御。デフォルト: `http://localhost:3000,https://pl-generator.vercel.app`
6. **Docker COPY** — 両Dockerfileは `services/worker/` と `services/api/` を相互にCOPYする（共有コード）

## DB Schema Summary (FK Relationships)

```
projects ──< documents     (project_id → projects.id)
projects ──< runs          (project_id → projects.id)
runs     ──< phase_results (run_id → runs.id)
runs     ──< edits         (run_id → runs.id)
runs     ──< jobs          (run_id → runs.id)
runs     ──< llm_audits    (run_id → runs.id)
jobs     ──> phase_results (result_ref → phase_results.id)  ← 重要！
```

## Agent Teams Definition

### Tier 1: Gate Agents (実装前に実行)

**Architect Agent** — アプローチの妥当性判断
- 実装前に「そもそもこのアプローチは正しいか」を検証
- Architecture Decisions に違反していないか確認
- 代替案がある場合は列挙して最適案を選択

**Schema Agent** — DB/API制約の事前確認
- `infra/init.sql` を読み、FK/CHECK/UNIQUE制約を確認
- 変更対象テーブルの正しいリレーションを明示
- Pydantic schemaとDB schemaの整合性検証

### Tier 2: Implementation Agents (並列実行)

**Backend Agent** — Python/FastAPI/Celery
- 対象: `services/api/`, `services/worker/`, `src/`, `core/`, `shared/`
- Pydantic v2 (.model_dump()) を厳守
- logger.exception() でスタックトレース出力

**Frontend Agent** — TypeScript/React/Next.js
- 対象: `apps/web/`
- TanStack Query のポーリングロジック: エラー時もポーリング継続
- API URLは環境変数 `NEXT_PUBLIC_API_URL` から取得

**Infra Agent** — Docker/デプロイ設定
- 対象: `infra/`, `services/*/Dockerfile`, `render.yaml`, `apps/web/vercel.json`
- Docker COPYの漏れチェック必須
- render.yaml は1つだけ（ルートに配置）

### Tier 3: Verification Agents (実装後に実行)

**Test Agent** — テスト実行・品質検証
- `make test` を実行して全テスト通過を確認
- 新機能にはテストを追加

**Build Agent** — ビルド・構成検証
- `make build-check` でDocker build + Next.js build を検証
- 依存関係の整合性チェック

**Review Agent** — コードレビュー
- 横断パターンの一貫性 (Phase 2-5 が同じパターンか)
- セキュリティ (API key漏洩, SQL injection)
- Architecture Decisions 違反の検出

## Common Commands

```bash
# テスト実行
make test                    # pytest (root + API tests)
make test-api                # API tests only
make lint                    # Python lint check

# ビルド検証
make build-check             # Docker + Next.js build verification
make docker-build-api        # API Docker image build
make docker-build-worker     # Worker Docker image build

# ローカル開発
make dev                     # Docker Compose up (postgres + redis + api + worker)
make dev-frontend            # Next.js dev server

# 品質チェック
make ci                      # Full CI: lint + test + build-check
```

## File Scope Rules

| Agent | Writable Files | Read-Only |
|-------|---------------|-----------|
| Backend | `services/`, `src/`, `core/`, `shared/` | `infra/init.sql`, `apps/web/` |
| Frontend | `apps/web/` | `shared/schemas/`, `services/api/app/routers/` |
| Infra | `infra/`, `Dockerfile*`, `render.yaml`, `*.json` (root) | All source code |
| Test | `tests/`, `services/api/tests/` | All source code |

## 基本方針

- 必ず日本語で応対してください
- 調査やデバッグにはサブエージェントを活用してコンテキストを節約してください
- 重要な決定事項は定期的にマークダウンファイルに記録してください

## コード規約

- TypeScriptを使用
- テストはVitestで書く
- コミットメッセージは日本語で簡潔に

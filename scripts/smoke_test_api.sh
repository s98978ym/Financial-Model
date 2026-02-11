#!/usr/bin/env bash
# ============================================================
# PL Generator API Smoke Test
# ============================================================
# Usage:
#   ./scripts/smoke_test_api.sh                          # defaults to localhost:8000
#   ./scripts/smoke_test_api.sh https://plgen-api.onrender.com
#
# Tests the full Phase 1→5 pipeline via curl.
# Exits 0 if all pass, 1 on first failure.
# ============================================================

set -euo pipefail

API="${1:-http://localhost:8000}"
PASS=0
FAIL=0
PROJECT_ID=""
DOC_ID=""
JOB_ID=""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ── Helpers ─────────────────────────────────────────────────

assert_status() {
  local label="$1" expected="$2" actual="$3"
  if [ "$actual" = "$expected" ]; then
    echo -e "  ${GREEN}✓${NC} ${label} (HTTP ${actual})"
    PASS=$((PASS + 1))
  else
    echo -e "  ${RED}✗${NC} ${label} — expected ${expected}, got ${actual}"
    FAIL=$((FAIL + 1))
  fi
}

assert_json_field() {
  local label="$1" json="$2" field="$3"
  local val
  val=$(echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$field','__MISSING__'))" 2>/dev/null || echo "__ERROR__")
  if [ "$val" != "__MISSING__" ] && [ "$val" != "__ERROR__" ]; then
    echo -e "  ${GREEN}✓${NC} ${label} → ${field}=${val}"
    PASS=$((PASS + 1))
  else
    echo -e "  ${RED}✗${NC} ${label} — field '${field}' missing"
    echo "     Response: $(echo "$json" | head -c 200)"
    FAIL=$((FAIL + 1))
  fi
}

poll_job() {
  local job_id="$1" max_wait="${2:-120}" interval=3 elapsed=0
  while [ $elapsed -lt $max_wait ]; do
    local resp
    resp=$(curl -sf "${API}/v1/jobs/${job_id}" 2>/dev/null || echo '{"status":"error"}')
    local status
    status=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "unknown")

    case "$status" in
      completed)
        echo -e "  ${GREEN}✓${NC} Job ${job_id} completed (${elapsed}s)"
        PASS=$((PASS + 1))
        return 0
        ;;
      failed)
        local err
        err=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('error_msg',''))" 2>/dev/null || echo "")
        echo -e "  ${RED}✗${NC} Job ${job_id} failed: ${err}"
        FAIL=$((FAIL + 1))
        return 1
        ;;
      queued|running)
        local prog
        prog=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('progress',0))" 2>/dev/null || echo "?")
        printf "  … Job %s: %s (%s%%) [%ds]\r" "$job_id" "$status" "$prog" "$elapsed"
        ;;
      *)
        printf "  … Job %s: %s [%ds]\r" "$job_id" "$status" "$elapsed"
        ;;
    esac

    sleep $interval
    elapsed=$((elapsed + interval))
  done

  echo -e "\n  ${RED}✗${NC} Job ${job_id} timed out after ${max_wait}s"
  FAIL=$((FAIL + 1))
  return 1
}

# ── Tests ───────────────────────────────────────────────────

echo -e "\n${YELLOW}═══ PL Generator API Smoke Test ═══${NC}"
echo -e "Target: ${API}\n"

# 1. Health check
echo -e "${YELLOW}[1/9] Health Check${NC}"
HTTP_CODE=$(curl -so /dev/null -w "%{http_code}" "${API}/health" 2>/dev/null || echo "000")
assert_status "GET /health" "200" "$HTTP_CODE"

if [ "$HTTP_CODE" = "000" ]; then
  echo -e "\n${RED}API unreachable at ${API}. Is the server running?${NC}"
  exit 1
fi

# 2. Create project
echo -e "\n${YELLOW}[2/9] Create Project${NC}"
RESP=$(curl -s -w "\n%{http_code}" -X POST "${API}/v1/projects" \
  -H "Content-Type: application/json" \
  -d '{"name":"Smoke Test Project"}')
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "POST /v1/projects" "201" "$HTTP_CODE"
assert_json_field "Project created" "$BODY" "id"
PROJECT_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")

if [ -z "$PROJECT_ID" ]; then
  echo -e "${RED}Cannot continue without project_id${NC}"
  exit 1
fi

# 3. Upload document (text mode)
echo -e "\n${YELLOW}[3/9] Upload Document (text)${NC}"
SAMPLE_TEXT="当社は法人向けSaaSプラットフォームを提供しています。月額課金モデルで、現在100社の顧客を持ち、ARRは1.2億円です。主要コストはエンジニア人件費（60%）とクラウドインフラ（20%）です。来期はARR2倍を目指します。"
RESP=$(curl -s -w "\n%{http_code}" -X POST "${API}/v1/documents/upload" \
  -F "project_id=${PROJECT_ID}" \
  -F "kind=text" \
  -F "text=${SAMPLE_TEXT}")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "POST /v1/documents/upload" "201" "$HTTP_CODE"
assert_json_field "Document uploaded" "$BODY" "id"
DOC_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")

if [ -z "$DOC_ID" ]; then
  echo -e "${RED}Cannot continue without document_id${NC}"
  exit 1
fi

# 4. Phase 1 — Template Scan (synchronous)
echo -e "\n${YELLOW}[4/9] Phase 1: Template Scan${NC}"
RESP=$(curl -s -w "\n%{http_code}" -X POST "${API}/v1/phase1/scan" \
  -H "Content-Type: application/json" \
  -d "{\"project_id\":\"${PROJECT_ID}\",\"document_id\":\"${DOC_ID}\"}")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "POST /v1/phase1/scan" "200" "$HTTP_CODE"
assert_json_field "Phase 1 result" "$BODY" "catalog"

# 5. Phase 2 — BM Analysis (async)
echo -e "\n${YELLOW}[5/9] Phase 2: Business Model Analysis${NC}"
RESP=$(curl -s -w "\n%{http_code}" -X POST "${API}/v1/phase2/analyze" \
  -H "Content-Type: application/json" \
  -d "{\"project_id\":\"${PROJECT_ID}\",\"document_id\":\"${DOC_ID}\"}")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "POST /v1/phase2/analyze" "202" "$HTTP_CODE"
assert_json_field "Phase 2 job queued" "$BODY" "job_id"
JOB_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('job_id',''))" 2>/dev/null || echo "")

if [ -n "$JOB_ID" ]; then
  echo "  Polling job ${JOB_ID}..."
  poll_job "$JOB_ID" 180
fi

# 6. Phase 3 — Template Mapping (async)
echo -e "\n${YELLOW}[6/9] Phase 3: Template Mapping${NC}"
RESP=$(curl -s -w "\n%{http_code}" -X POST "${API}/v1/phase3/map" \
  -H "Content-Type: application/json" \
  -d "{\"project_id\":\"${PROJECT_ID}\"}")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "POST /v1/phase3/map" "202" "$HTTP_CODE"
assert_json_field "Phase 3 job queued" "$BODY" "job_id"
JOB_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('job_id',''))" 2>/dev/null || echo "")

if [ -n "$JOB_ID" ]; then
  echo "  Polling job ${JOB_ID}..."
  poll_job "$JOB_ID" 180
fi

# 7. Phase 4 — Model Design (async)
echo -e "\n${YELLOW}[7/9] Phase 4: Model Design${NC}"
RESP=$(curl -s -w "\n%{http_code}" -X POST "${API}/v1/phase4/design" \
  -H "Content-Type: application/json" \
  -d "{\"project_id\":\"${PROJECT_ID}\"}")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "POST /v1/phase4/design" "202" "$HTTP_CODE"
assert_json_field "Phase 4 job queued" "$BODY" "job_id"
JOB_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('job_id',''))" 2>/dev/null || echo "")

if [ -n "$JOB_ID" ]; then
  echo "  Polling job ${JOB_ID}..."
  poll_job "$JOB_ID" 180
fi

# 8. Phase 5 — Parameter Extraction (async)
echo -e "\n${YELLOW}[8/9] Phase 5: Parameter Extraction${NC}"
RESP=$(curl -s -w "\n%{http_code}" -X POST "${API}/v1/phase5/extract" \
  -H "Content-Type: application/json" \
  -d "{\"project_id\":\"${PROJECT_ID}\"}")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "POST /v1/phase5/extract" "202" "$HTTP_CODE"
assert_json_field "Phase 5 job queued" "$BODY" "job_id"
JOB_ID=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('job_id',''))" 2>/dev/null || echo "")

if [ -n "$JOB_ID" ]; then
  echo "  Polling job ${JOB_ID}..."
  poll_job "$JOB_ID" 180
fi

# 9. Project state (verify all phase results)
echo -e "\n${YELLOW}[9/9] Verify Project State${NC}"
RESP=$(curl -s -w "\n%{http_code}" "${API}/v1/projects/${PROJECT_ID}/state")
HTTP_CODE=$(echo "$RESP" | tail -1)
BODY=$(echo "$RESP" | sed '$d')
assert_status "GET /v1/projects/{id}/state" "200" "$HTTP_CODE"
assert_json_field "Project state" "$BODY" "current_run_id"

# Check which phases completed
PHASE_COUNT=$(echo "$BODY" | python3 -c "
import sys, json
d = json.load(sys.stdin)
pr = d.get('phase_results', {})
print(len(pr))
" 2>/dev/null || echo "0")
echo -e "  Phase results stored: ${PHASE_COUNT}"

# ── Summary ─────────────────────────────────────────────────

echo -e "\n${YELLOW}═══ Summary ═══${NC}"
TOTAL=$((PASS + FAIL))
echo -e "  Total: ${TOTAL}  ${GREEN}Pass: ${PASS}${NC}  ${RED}Fail: ${FAIL}${NC}"

if [ "$FAIL" -gt 0 ]; then
  echo -e "\n${RED}SMOKE TEST FAILED${NC}"
  exit 1
else
  echo -e "\n${GREEN}ALL SMOKE TESTS PASSED${NC}"
  exit 0
fi

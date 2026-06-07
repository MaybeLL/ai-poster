# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

AI Poster is an automated content production system for AI industry news. It ingests RSS sources, clusters events, builds research packets, generates draft articles, runs quality checks, and publishes to content platforms.

## Commands

### Installable CLI (`ai-poster`)

```bash
pip install -e .

# Quick demo with mock QA scores
ai-poster demo --topic "OpenAI releases a new coding model"

# Ingest RSS sources
ai-poster ingest --lookback-hours 24
ai-poster --json ingest --lookback-hours 24  # machine-readable output

# Rank event clusters
ai-poster events --lookback-hours 24 --limit 3

# Build research packets
ai-poster research --lookback-hours 24 --limit 3

# Full pipeline (ingest → cluster → research → draft → QA → publish)
ai-poster pipeline --lookback-hours 24 --limit 1

# Probe/smoke-test the intelligence backend
ai-poster agent probe
ai-poster agent smoke

# Start the web API
ai-poster serve --port 8000

# Database migrations
ai-poster migrate upgrade head
ai-poster migrate current
ai-poster migrate history

# Run unit tests
python3 -m unittest discover -s tests/unit -p 'test_*.py'
```

Global options: `--json` (machine-readable output), `--env-file PATH` (load .env file).

### Legacy CLI (`python -m app`)

```bash
python3 -m app --mode demo-workflow --topic "..."
python3 -m app --mode ingest --lookback-hours 24
python3 -m app --mode pipeline --lookback-hours 24 --limit 1
python3 -m app --mode agent-probe
python3 -m app --mode agent-smoke
```

## Key environment variables

- `AI_POSTER_INTELLIGENCE_BACKEND` — `rule` (default), `codex`, or `claude-code`. Controls which external process handles research/writing/QA.
- `AI_POSTER_CODEX_COMMAND` / `AI_POSTER_CLAUDE_CODE_COMMAND` — override the default CLI command for the respective backend.
- `AI_POSTER_CODEX_ENV_JSON` / `AI_POSTER_CLAUDE_CODE_ENV_JSON` — inject env vars into the external process (JSON object string).
- `AI_POSTER_ENV` — runtime environment, default `development`.
- `AI_POSTER_DATA_DIR` — data directory, default `data` (contains `sources.json`).

## Architecture

The system is a pipeline with three layers:

**1. Intelligence layer** (`app/agents/`)
- `AgentProvider` protocol: `generate(request) -> AgentResponse`
- `ProcessAgentProvider` is the default implementation — it shells out to an external CLI process via `subprocess.run`.
- `AgentProfile` protocol defines how to build the CLI invocation (`build_invocation`) and parse the result (`parse_result`). Concrete profiles: `ClaudePrintProfile`, `CodexExecProfile`, `StdinJsonProfile`.
- `factory.py` wires `AppSettings` → `ProcessAgentProvider` based on `AI_POSTER_INTELLIGENCE_BACKEND`.

**2. Service layer** (`app/services/`)
- **ingestion**: `IngestionService` reads `data/sources.json`, fetches RSS feeds via `httpx`, and filters by time window.
- **events**: `EventEngine` clusters documents by title token overlap (Jaccard ≥ 0.6), ranks by freshness/authority/coverage, and selects top-N.
- **research**: `ResearchService` builds structured `ResearchPacket` from event clusters. `AgentResearchService` delegates to the external agent with rule-based fallback.
- **writing**: `WritingService` generates template-based long/short drafts. `AgentWritingService` delegates the same way.
- **qa**: `QaService` runs rule-based review producing `QualityGateInput`. `AgentQaService` delegates similarly.
- `services/factory.py` assembles `ContentServices` (research + writing + QA), picking agent or rule variants based on whether `build_agent_provider` returns a provider or `None`.

**3. Core domain** (`app/core/`)
- `ContentJob` is a strict forward-only state machine with 14 pipeline stages (`created → ingested → ... → accepted/rejected → exported`). Supports `rewind_to` for non-terminal rollback.
- `QualityGate` enforces hard score thresholds (total ≥ 80, factual ≥ 90, clarity ≥ 75) plus boolean checks.

**Workflow** (`app/workflows/`):
- `MvpWorkflowRunner` is the minimal end-to-end runner: creates a `ContentJob`, advances through all stages, runs quality gate, returns result.

## Source configuration

`data/sources.json` lists RSS feeds with `source_id`, `url`, `kind` (only `"rss"` supported), `enabled`, and `authority_weight` (1–10). Sources with higher weight get priority in clustering and ranking.

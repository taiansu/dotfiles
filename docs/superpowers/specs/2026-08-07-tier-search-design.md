# Tier Search Design

**Status:** Approved for planning  
**Date:** 2026-08-07

## Purpose

Provide an OMP skill and extension tool that autonomously searches only when external or time-sensitive evidence is needed. It must query providers in a user-configured order, fall through only when a provider's results fail explicit quality checks, and constrain its own estimated spending without pretending to be the billing authority.

## Goals

- Provide a skill that directs the agent to use tiered search for current external facts, official documentation, prices, policy or legal information, citations, and user-provided URLs.
- Query only the configured providers, in their configured order.
- Fall through only when source quality fails deterministic, inspectable criteria.
- Let the user configure a separate estimated monthly USD budget for each provider.
- Keep Kagi available to OMP's built-in `web_search`; the tier-search tool only accounts for searches it initiates itself.
- Report provider choice, quality failures, estimated cost, and provider-local monthly strategy usage for every tool call.

## Non-goals

- Do not modify OMP core or its built-in `web_search` provider chain.
- Do not claim a local ledger is the provider's actual billing state.
- Do not prevent other tools, programs, devices, or direct API calls from spending on the same provider account.
- Do not use an LLM as an opaque relevance or quality judge.
- Do not guarantee factual correctness from search results.

## Components

### Skill

Install `~/.claude/skills/tier-search/SKILL.md`.

The skill is policy only. It tells the agent to call `tier_web_search` when external or time-sensitive evidence is required, and not to search for questions answerable from the current repository or conversation. It does not execute network requests or enforce a budget.

### Extension

Install `~/.omp/agent/extensions/tier-web-search.ts`.

The extension registers the model-callable `tier_web_search` tool. It is the sole implementation of provider selection, source normalization, quality gates, metadata enrichment, cost estimation, and strategy-budget tracking.

The extension uses provider API credentials from the existing environment or OMP credential store. It must never emit secret values.

### Configuration

Use an extension-owned global file rather than unrecognized fields in OMP's core configuration:

```yaml
# ~/.omp/agent/tier-web-search.yml
version: 1

providers:
  - id: tavily
    estimated_monthly_budget_usd: 10
  - id: brave
    estimated_monthly_budget_usd: 8
  - id: kagi
    estimated_monthly_budget_usd: 24
```

Rules:

- The array order is the provider attempt and fallback order.
- `id` is unique and initially restricted to `tavily`, `brave`, or `kagi`.
- `estimated_monthly_budget_usd` is a finite non-negative USD value.
- A zero budget disables that provider.
- Unknown IDs, duplicate IDs, malformed YAML, or invalid values fail closed before any provider request.
- The extension uses a versioned conservative request-cost estimator for its fixed search endpoints. Version 1 reserves the pay-as-you-go price while ignoring included credits: Tavily basic search `$0.008`, Brave Search `$0.005`, and Kagi Search `$0.012` per request. The user configures only provider budgets, not fragile provider unit prices.
- The budget is a strategy policy. It applies only to calls made by `tier_web_search`; it is not reconciled against OMP's built-in `web_search` or any external usage.

## Provider-side billing controls

Provider-side limits remain the real billing boundary. Kagi's API Portal exposes a USD Usage Limit; configure it independently from the extension's Kagi strategy budget. Configure equivalent provider-side spend limits or alerts for Tavily and Brave when the user's plan supports them.

The extension must call the fixed, cost-modelled search endpoint for each provider. A provider price or plan change requires a deliberate update to the extension's estimator and tests.

## Budget ledger

Maintain a local, shared ledger under the active OMP agent directory. Its entries are bucketed by UTC `YYYY-MM` and provider ID. Store every configured budget and reservation as integer micro-USD to avoid floating-point boundary errors.

Before a provider request, atomically reserve its conservative estimated cost. If the reservation would exceed that provider's configured budget, skip that provider and record `estimated_budget_reached`. On request failure or cancellation, roll back the reservation. On success, retain it.

The ledger's purpose is to make behavior consistent across local OMP sessions and to prevent this tool from repeatedly reaching expensive fallback providers. It is an estimate, not accounting.

## Tool contract

`tier_web_search` accepts:

- `query` (required)
- `recency` (`day`, `week`, `month`, or `year`; optional)
- `max_results` (optional)

For each configured provider, it:

1. Validates availability and remaining estimated budget.
2. Reserves the estimated per-request cost.
3. Calls the provider's fixed search endpoint.
4. Normalizes URLs, titles, snippets, publication dates, and provider metadata.
5. Enriches selected source identities when applicable.
6. Evaluates the deterministic quality gate.
7. Stops at the first provider that passes, otherwise records the failure reasons and continues.

If every provider fails a quality gate or is skipped, return the highest-scoring non-empty normalized result set. Never fabricate an answer or sources. If no provider yields renderable content, return a structured error.

The result contains final sources plus structured details:

- selected provider, or `none`
- every attempted provider
- attempted provider's normalized source count and quality score
- applicable quality failures
- skipped-provider reasons
- reserved request estimate and UTC-month provider strategy usage
- source identities and their confidence

## Quality gate

A provider must pass every applicable criterion:

| Criterion | Pass condition | Applies when |
| --- | --- | --- |
| Source count | At least three usable sources | Always |
| Source diversity | At least two canonical source identities; no identity contributes more than two counted sources | Always |
| Query relevance | At least 60% of distinct meaningful query terms appear in the combined title/snippet text of the top three sources; every quoted phrase, `site:` host, and URL constraint must match at least one source | Always |
| Freshness | At least one result satisfies the requested or explicitly stated recency requirement | A recency constraint exists |
| Authoritative source | At least one source matches a user-provided URL or explicit `site:` constraint | The user explicitly demands an official source or supplies that constraint |

Meaningful terms are Unicode word segments of at least three characters, plus CJK word segments of at least two characters, after removing punctuation only. The implementation uses `Intl.Segmenter` where available and a Unicode word-sequence fallback otherwise.

The quality score used solely to choose the best non-empty result after all providers fail is a normalized weighted sum of source count (25), source diversity (25), query-term coverage (30), freshness (10), and authority (10). Inapplicable freshness and authority dimensions are removed from both the numerator and denominator before normalization.

The tool intentionally does not claim universal knowledge of a brand's official domain. In the absence of an explicit domain or URL, it reports evidence quality rather than inventing an authority judgement.

A failed criterion produces a stable reason: `insufficient_sources`, `low_source_diversity`, `low_query_coverage`, `stale_results`, or `missing_authoritative_source`.

## Canonical source identity

### Ordinary sites

Use the Public Suffix List to derive the registrable domain, not a hand-written last-two-label rule. Thus `platform.openai.com` and `help.openai.com` both map to `openai.com`, while `docs.example.co.uk` maps to `example.co.uk`.

### GitHub

For `github.com/<owner>/<repo>/...`, the initial identity is `github:<owner>/<repo>`.

For at most five GitHub candidates per search, fetch repository metadata. If it explicitly reports `fork: true` and a `parent`, replace the identity with the parent repository. If metadata is unavailable, rate limited, invalid, or incomplete, retain the repository identity with `fallback` confidence and do not block the search.

### Hugging Face

For Hugging Face, identity is `<type>:<author>/<repo>`, where type is `model`, `dataset`, or `space`. Query the matching public Hub metadata endpoint for at most five candidates.

Only collapse a Hugging Face identity when returned metadata or page metadata explicitly proves an upstream or duplicate lineage. Hugging Face's public metadata does not generally expose GitHub-style fork-parent lineage, so absence of proof leaves repositories distinct. Metadata failure degrades to the URL-derived identity with `fallback` confidence and never blocks search.

### Medium

`medium.com/@<author>/...` is an author identity, and `<publication>.medium.com/...` is a publication identity. For up to five remaining ambiguous Medium candidates, fetch the public page and inspect JSON-LD or author metadata. Resolve to an author identity when present; otherwise degrade to publication or `medium.com` identity with `fallback` confidence.

GitHub, Hugging Face, and Medium metadata cache entries expire after seven days. Lookups must time out after three seconds, read at most 512 KiB, and have no effect on the main search result if they fail.

## Error handling and safety

- Respect tool cancellation throughout provider calls, metadata fetches, and ledger updates.
- Provider errors, timeouts, empty results, invalid responses, and metadata failures are recorded per attempt and cause sequential fallback when another provider remains.
- Do not perform provider fan-out in parallel; ordered fallback is intentional cost control.
- Never persist API credentials in the configuration, ledger, tool results, or logs.
- Cap metadata enrichment to five candidates per supported host and use per-host timeouts.

## Verification requirements

- Unit-test configuration validation, provider ordering, disabled providers, and UTC month rollover.
- Unit-test atomic reservation, rollback on failure/cancellation, and skip behavior at a budget boundary.
- Unit-test every quality-gate reason and the all-failed best-non-empty-result selection.
- Unit-test Public Suffix List canonicalization, GitHub parent-fork collapsing, Hugging Face explicit-lineage collapsing, Medium author extraction, and all fallback-confidence paths.
- Mock provider and metadata HTTP responses; tests must not consume API credits.
- Add a smoke scenario with mocked Tavily failure, Brave quality failure, and Kagi success, verifying ordered attempts and structured diagnostics.
- Manually verify vendor-side limits independently; especially verify Kagi's Usage Limit behavior in the API Portal before relying on it as a billing control.

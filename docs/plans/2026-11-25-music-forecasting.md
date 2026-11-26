# Music Forecasting Implementation Plan

**Goal** — Run reproducible, point-in-time experiments and measure whether new signals improve 90-day chart-entry forecasts.

**Architecture** — Use Recoup API for authenticated measurement and audio access, Supabase for scoped provenance and experiment state, private Supabase Storage for licensed inputs, and Modal for compute. Vercel Workflows coordinate data jobs once the licensed inputs can be qualified. The open repository owns benchmark definitions, the evaluator, and reproducible public evidence.

## Critical path and dependencies

| Step | Deliverable | Dependency and exit check |
| --- | --- | --- |
| 1 | Freeze a small public proxy, cohort and dates before acquisition | Wikimedia Analytics API, available under CC0. Check complete daily responses and snapshot hashes. |
| 2 | Run the full proxy through candidate selection, rolling features, walk-forward ranking and paired evaluation | Frozen input, strict date joins, horizon purge, deterministic baseline and challenger configs. Publish the exact command, checksums and test results. |
| 3 | Qualify historical labels and the release universe for HIT-100 | Obtain Luminate/Billboard chart editions, original publication times, identifiers, revisions, and an independently sampled US release feed containing non-charting music. Confirm internal research, derivative output and retention terms in writing. |
| 4 | Qualify historical features with Recoup | Start with `GET /api/research/tracks/{id}/measurements` and `GET /api/research/track/historic-stats`. Reconcile a bounded sample with source vintage records. Use a separately authorized measurement job only for approved cohort members with gaps and a known credit budget. |
| 5 | Run the licensed performance-only benchmark | Freeze chart and release manifests, coverage, first-entry mapping, manifest cutoff, split dates and feature availability policy. Run a restricted evaluator and record all results. |
| 6 | Acquire and process a matched audio sample | Start with opt-in rights-holder masters from the same eligible release universe. Open audio can exercise extraction. Verify rights, identity, audio storage, processing region, retention and approval to keep or publish derived features. |
| 7 | Run controlled audio ablations | Compare performance-only with performance plus audio on identical candidates and cutoffs. Record missingness and test whether coverage itself predicts the outcome. |
| 8 | Add cloud orchestration and prospective verification | Prerequisites are an authorized Supabase project, Vercel project and Modal workspace, named owners for creds and spend, a data manifest that passes qualification, and reproducible local runs. Register a prospective series before looking at outcomes. |

## Acquisition specification

### Chart outcomes and releases

- Request a Luminate API export or licensed data share for weekly US Hot 100 editions. Ask for edition IDs, original publication timestamps, revision lineage, ordered ranks and recording identifiers. Use contiguous completeness checks and quarantine revisions without a reliable vintage. Do not infer chart publication from a chart's nominal date.
- For first-ever entry, request complete prior history or an authoritative previously-charted indicator and define whether versions are grouped by the chart provider. If prior history is incomplete, report first observed entry under a separate benchmark ID.
- Build the candidate universe from a time-stamped, geographically scoped distributor or label release feed independent of chart success. Use MusicBrainz core fields for crosswalk enrichment where coverage is adequate. Record ISRC and MusicBrainz recording ID separately from composition and provider chart IDs. Retain ambiguous matches for manual review and report join rates for both charting and non-charting recordings.
- Start with an entitlement and QA sample of eight contiguous export weeks, rank and identity reconciliation, and several hundred independently sampled releases. Size the production benchmark by eligible positives, calendar coverage and achievable confidence interval width before freezing its holdout. Include a full 90-day maturity buffer and a prior-history audit.

References [Luminate Music API chart endpoints](https://docs.luminatedata.com/changelog/music-api-updates) · [MusicBrainz core data license](https://musicbrainz.org/doc/About/Data_License)

### Performance signals

- Start with a rights-cleared ISRC set. Inspect fields and measured overlap using authenticated Recoup track measurements, catalog measurements for an authorized catalog, and historic stats where source vintages can be verified. Existing reads can charge credits, and measurement jobs can enqueue billable historical backfill.
- Current track measurements return `date`, `value` and `data_source`. For historical evaluation, require independent publication or ingestion evidence for each vintage. A present-day backfill alone cannot prove a past information cutoff. Begin prospective capture now once the cohort and source authority exist.
- If needed, add append-only observation vintages in `recoupable/database`; use service-owned ingestion plus organization-scoped read policies. Keep occurrence, original availability, capture and revision times distinct. Reuse Recoup auth and the measurement domain functions in `recoupable/api`. Add a versioned snapshot export endpoint only when the existing reads and input contract cannot deliver the required vintages. Test cross-organization denial, nullable availability, revisions, pagination and idempotency.

References [Recoup track measurements](https://docs.recoupable.dev/api-reference/research/tracks-measurements) · [Measurement jobs](https://docs.recoupable.dev/api-reference/research/measurement-jobs)

### Audio and feature extraction

- Prefer authorized WAV/FLAC manifests from an opted-in label or distributor, covering eligible and never-charting recordings. Ask whether research use, transformation, hosted processing, derived feature retention and aggregate publication are permitted. Record agreement reference, ISRC, version, checksum, availability, storage key, region, expiry and deletion contact. Music metadata access does not provide recording access.
- Inspect per-track terms for open audio candidates such as Free Music Archive. Use those recordings to qualify extraction and storage independently of the chart cohort. Treat streaming previews and public listening links as discovery metadata until their terms explicitly permit this use.
- Use private Supabase Storage keys scoped to the organization and short-lived URL issuance after authorization. Hash inputs before feature extraction. Use CPU workers on Modal first for stable duration, loudness, dynamics, tempo, and spectral features. Freeze extractor/code versions and stream or delete raw bytes as the agreement requires.
- Qualify Recoup's Modal-backed `analyze_music` MCP tool for a small semantic ablation using its existing presets. Record exact model and prompt, cap concurrency and cost, and treat descriptors from a model with an unknown training cutoff as exploratory. Prefer deterministic signal processing as the first audio baseline.

References [FMA dataset paper](https://arxiv.org/abs/1612.01840) · [Supabase private storage](https://supabase.com/docs/guides/storage/security/access-control) · [Modal batch processing](https://modal.com/docs/guide/batch-processing)

## Evaluation and release gates

1. For HIT-100, define a weekly UTC cutoff and rank released, eligible recordings with no prior observed chart entry. Resolve the label with the first official publication in (cutoff, cutoff + 90 days]. Missing release or chart coverage is unresolved. Require at least 100 eligible candidates for Precision@100.
2. Version every dataset and freeze a rolling-origin development period, validation period and untouched test period. Purge training labels unresolved at each prediction cutoff. Compare stable random, popularity, momentum and regularized logistic baselines. Select one challenger on validation and score it once against the validation-selected strongest simple baseline. Keep the complete leaderboard for validation.
3. Report weekly candidate counts, few/zero-positive weeks, Precision@K, recall, Brier score for probability models, and paired moving-block interval over dates spanning at least the outcome overlap. Review variance by market, calendar era, missingness and artist. Make a positive aggregate claim only if the predeclared primary metric improves with a paired interval above zero and coverage remains fixed.
4. Validate incrementally through `python -m unittest discover -s tests -v`, the public CLI, then the cloud preview with retries and duplicate submissions. Persist a deterministic key from dataset hash, strategy version, cutoff and config so retries reuse results. Run provider and access qualification before any production schedule.
5. Use Vercel Workflows for durable orchestration and Modal batch execution for bounded parallelism. Start with an enumerated experiment grid and one owner of holdout evaluation. Consider a Recoup swarm, using Flex for architectural reference only, if experiment throughput becomes the limiting dependency after dataset qualification.
6. Forecast prospectively, register the prediction hash and version before outcomes publish, and score resolved cohorts after the final label window. A prospective 90-day chart claim requires that full observation period.

References [Vercel Workflows](https://vercel.com/workflows) · [Wikimedia Analytics API access policy](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/documentation/access-policy.html)

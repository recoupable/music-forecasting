# Data delivery for a verified HIT-100

The first archive replay uses historical issue dates, current release metadata, and title/artist joins. The verified benchmark needs two independently frozen inputs for the same time range. Ask about a sample and entitlements before ordering an export.

| Owner | Minimum export | What it resolves |
| --- | --- | --- |
| Luminate or Billboard | US Billboard Hot 100 chart ID, every weekly edition from July 2022 through April 2025, original full-chart publication timestamp with time zone, issue date, rank, revision publication timestamps, stable chart entity ID per entry, and chart-to-ISRC membership with effective dates. Include an authoritative earliest-ever entry per entity or enough older history to reconstruct it. | Whether a song had already charted at a forecast cutoff, whether it first entered within 90 days, and which versions count together. |
| Distributor or authorized multi-label data provider | All U.S. digital audio delivery and availability events from January 2022 through December 2024 for one fully covered catalog or panel. Include ISRC, release ID or UPC, titles, artists, version links, U.S. go-live timestamp, record delivery/first-seen timestamp, removals and corrections. Include low- and zero-play releases as well as releases that later charted. | Which recordings belonged in each weekly candidate pool and when they became eligible. |
| Songstats or Recoup measurement owner | Optional dated Spotify observations for the panel with observation period, first-seen timestamp, revision history, platform/market, ISRC, and metric definition. Confirm approved analysis, retention and aggregate output terms. | Whether performance signals improve the metadata and artist-history baselines on the same cohort. |

## Sample and acceptance

- Start with eight consecutive Hot 100 issues and the matching distributor period, plus prior chart flags and 90-day outcome coverage for the sample cutoffs. Ask for source IDs and documented publication events rather than an inferred schedule.
- Verify all 100 unique ranks per issue and reconcile every entry affecting an evaluated cutoff or horizon boundary. Require a distinction between first issue publication and later corrections.
- Freeze the distributor roster and selection rules before looking at chart outcomes. Reconcile release counts by week and confirm null or zero activity is covered. Keep version conflicts and unresolved identities out of binary labels, and report how many remain unresolved.
- Confirm at least 100 eligible recordings per cutoff, enough distinct future entrants for a meaningful held-out interval, and a 90-day maturity buffer. Retain both observed dates and original availability timestamps in the restricted source files. Keep all source terms and any approval references with the manifest.
- Deploy no provider-specific endpoint until the private bundle and baseline can be reproduced locally. Export the qualified projection into the existing [HIT-100 input contract](benchmark-inputs.md).

[Luminate chart catalog](https://docs.luminatedata.com/reference/get-charts) · [Luminate Music Data Share chart tables](https://docs.luminatedata.com/docs/charts)

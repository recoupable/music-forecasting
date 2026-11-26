# Benchmark inputs

## Public attention replay

The [cohort](../experiments/attention-cohort.json) defines a fixed panel of English Wikipedia song pages and weekly cutoffs. Candidate selection removes the eight most viewed pages in the trailing 28 available days. A positive enters the eight most viewed in the next 28 days. The replay assigns daily counts a seven-day availability lag and separately waits for the lag before using labels for model training. The snapshot contains current historical counts and has no publication or revision log, so the lag is a research assumption. The convenience panel favors established songs and requires complete coverage. It measures song-page attention.

The evaluation fits on pre-validation history, selects models on validation Precision@5, then refits the chosen challenger on all matured pre-holdout labels. The held-out weekly comparison uses a seeded five-week circular block bootstrap to account for overlapping outcomes. A longer dependence structure would need separate sensitivity analysis. The published report includes every weekly precision pair. A confirmatory extension needs a fresh cutoff range or cohort, and a protocol frozen before scoring.

## Private HIT-100 bundle

Build this JSON projection inside an approved research workspace. The chart command accepts one metric in additive daily units (e.g. daily streams). Convert cumulative counts into properly dated deltas upstream. Keep original publication timestamps, original source records, coverage evidence, ingestion timestamps, and the identity crosswalk in the restricted data layer. Round an input's availability up to the first UTC midnight at which it was knowable. Project official chart publication timestamps to that same boundary for `first_chart_on`. The horizon and the declared chart coverage end are measured at UTC midnight.

```json
{
  "benchmark": "hit-100",
  "first_cutoff": "2019-01-07",
  "validation_start": "2021-01-04",
  "test_start": "2023-01-02",
  "last_cutoff": "2024-09-30",
  "coverage": {
    "approval_ref": "internal-reference",
    "prior_chart_history_complete": true,
    "first_release_cutoff_covered": "2019-01-07",
    "last_release_cutoff_covered": "2024-09-30",
    "labels_complete_through": "2024-12-29"
  },
  "recordings": [
    {
      "id": "provider-approved-recording-id",
      "release_on": "2018-12-07",
      "release_available_on": "2018-12-08",
      "first_chart_on": null
    }
  ],
  "observations": [
    {
      "id": "provider-approved-recording-id",
      "occurred_on": "2019-01-03",
      "available_on": "2019-01-05",
      "value": 313
    }
  ]
}
```

The example shows the shape. A runnable bundle requires 100 or more eligible candidates per cutoff, complete chart history, mature labels, and both positive and negative training outcomes. Null chart entry means no entry through the declared coverage date. The cutoff excludes previously charted or unavailable recordings. Multiple observation vintages are allowed, and the runner picks the latest known vintage for that day. Missing observations remain missing and measurement coverage is reported as a feature in one challenger. Results and source approvals stay private unless the agreements permit publication. An operator must verify the approval and coverage declarations against the evidence.

```sh
python -m forecasting.chart /private/path/hit-100.json > .forecast/hit-100-results.json
```

## Audio manifest

The initial audio command accepts a rights-cleared 16-bit PCM WAV. It produces duration, RMS, peak and amplitude range. The manifest is an operator attestation. Confirm rights in the source agreement and retain the recording identity and checksum with each feature run.

```json
{
  "recording_id": "internal-recording-id",
  "approval_ref": "internal-reference",
  "available_on": "2020-06-01",
  "rights_expire_on": null,
  "allowed_processing": ["local"],
  "sha256": "<sha256 of WAV bytes>"
}
```

```sh
python -m forecasting.audio /private/path/input.wav /private/path/manifest.json --as-of 2021-01-01
```

Joining authorized audio features into the chart experiment is a subsequent ablation. See the [acquisition plan](plans/2026-11-25-music-forecasting.md) for the storage, retention and hosted execution dependencies.

The repository includes a [source manifest](../experiments/audio-smoke-manifest.json) and [feature report](../experiments/audio-smoke-results.json) for a public-domain “Russian rag” excerpt. The availability date is the date the input was acquired for this test. To reproduce, download the WAV at the manifest's `source_url` and pass it to the command above with `experiments/audio-smoke-manifest.json --as-of 2026-11-25`. The recording exercises the extractor independently of the chart cohort. [Citizen DJ Project, Library of Congress, National Jukebox](https://citizen-dj.labs.loc.gov/loc-jukebox-popular/use/)

# Music Forecasting

An open research framework for forecasting music and culture. Could we have predicted what would chart next using only the information available that week?

The proposed framework reconstructs historical snapshots, runs forecasting strategies against them, and scores predictions against observed outcomes. Every observation distinguishes when an event happened from when it became knowable. Historical backtests measure performance under a defined information boundary, and prospective forecasts test predictions against outcomes that are still unknown.

## First benchmark

The proposed **90-Day Chart Entry Benchmark (HIT-100)** ranks previously released recordings that have never entered the Billboard Hot 100 by their probability of entering in the next 90 days. It starts with simple baselines such as popularity and recent growth. Including releases that never chart helps account for survivorship bias.

## Reproduce the public pilot

The held-out pilot used 21 song pages and 152 weekly cutoffs. The selected challenger achieved 21.71% Precision@5 versus 20.66% for the strongest validation-selected baseline. The paired 95% interval for the +1.05 percentage-point difference includes zero. Wikipedia pageviews measure attention and the result does not establish any improvement in predicting chart entry.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m forecasting.benchmark
```

The versioned data snapshot is included. To collect a fresh snapshot from Wikimedia with curl, run `python -m forecasting.wikimedia --output .forecast/pageviews.csv.gz`. To replay the public snapshot in an authenticated Modal workspace, install the Modal SDK and run `modal run modal_benchmark.py`.

- [Public results and weekly scores](experiments/attention-results.json)
- [First HIT-100 archive replay](docs/hit-100-archive-replay.md)
- [HIT-100 vendor delivery contract](docs/hit-100-delivery-contract.md)
- [HIT-100 source qualification](docs/hit-100-source-qualification.md)
- [Chart and audio input contracts](docs/benchmark-inputs.md)
- [Implementation and acquisition plan](docs/plans/2026-11-25-music-forecasting.md)
- [Point-in-Time Music Forecasting RFC](SPEC.md)
- [Contribution guide](CONTRIBUTING.md)
- [Apache License 2.0](LICENSE)

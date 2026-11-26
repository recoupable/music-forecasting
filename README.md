# Music Forecasting

An open research framework for forecasting music and culture. Could we have predicted what would chart next using only the information available that week?

The proposed framework reconstructs historical snapshots, runs forecasting strategies against them, and scores predictions against observed outcomes. Every observation distinguishes when an event happened from when it became knowable. Historical backtests measure performance under a defined information boundary, and prospective forecasts test predictions against outcomes that are still unknown.

## First benchmark

The proposed **90-Day Chart Entry Benchmark (HIT-100)** ranks previously released recordings that have never entered the Billboard Hot 100 by their probability of entering in the next 90 days. It starts with simple baselines such as popularity and recent growth. Including releases that never chart helps account for survivorship bias.

## Research status

This repository contains a draft research specification. The simulator, CLI, datasets, and benchmark results are planned. The RFC's example scores are hypothetical.

- [Read the Point-in-Time Music Forecasting RFC](SPEC.md)
- [Contribute to the research](CONTRIBUTING.md)
- [Apache License 2.0](LICENSE)

# HIT-100 archive replay

This exploratory 90-day chart-entry backtest uses real MusicBrainz releases and archived Billboard Hot 100 editions. The [cohort and split configuration](../experiments/hit100-musicbrainz.json) fixes the period and uses all labels in the official development sample. The first eight-label projection yielded too few candidates to score, so the cohort was broadened before joining outcomes. See the [data delivery contract](hit-100-delivery-contract.md) for the inputs needed for a verified HIT-100.

## How the cohort was built

- The cohort comes from the official November 2026 MusicBrainz database sample. It includes official digital audio releases marked US or Worldwide in the sample. Worldwide is a catalog designation and still needs confirmation of actual U.S. availability.
- Follow sampled release editions to recording MBIDs and ISRCs. A recording qualifies only when a sampled eligible edition shares its earliest dated official release in the dump. A potentially earlier release with an incomplete date can exclude a later edition.
- Join the earliest observed chart issue by normalized title and full artist credit. Use nearby title and credit variants only to flag ambiguity. Quarantine collisions, shared ISRCs, and chart entries that predate the sampled release. A record without a detected match is a provisional negative under this method. Current metadata and missed joins can change positives and negatives.
- Each Monday, rank the remaining recordings released in the previous 180 days. Compare a seeded random rank, release recency, and the artist’s recent archive chart presence with logistic models using release age, pre-release counts in the sampled catalog, and prior chart activity. The artist’s chart feature sees only issues dated on or before the cutoff. No Songstats, audio, or future chart rows enter the features.
- Compare on chronological validation and a 2024 holdout. The seven-day issue-date sensitivity excludes matches whose eligibility or 90-day outcome depends on the assumed publication lead. The horizon exclusions use label information retrospectively and limit interpretation to the remaining pool. An issue-date-only replay shows the impact of that assumption. Neither mode recovers the actual publication timestamps.

[MusicBrainz database downloads](https://musicbrainz.org/doc/MusicBrainz_Database/Download) · [Community Hot 100 archive](https://github.com/mhollingshead/billboard-hot-100)

## First result

The release projection found **7,949 recordings across 1,192 editions**, including 6,296 recordings with an ISRC. The crosswalk found 14 normalized title/full-credit matches on or after the indexed release date. It flagged 369 recordings for version, title/credit, or chronological conflicts. The remaining 7,566 had no detected chart match.

| 2024 holdout | Weekly candidates | Positive recording-weeks | Artist-history baseline Precision@100 | Selected logistic Precision@100 |
| --- | ---: | ---: | ---: | ---: |
| Seven-day issue-date lead sensitivity | 886–1,283 | 1 | 0.0189% | 0.0189% |
| Issue date only | 886–1,283 | 2 | 0.0377% | 0.0377% |

Both runs cover 53 weekly cutoffs. The model tied the strongest simple baseline. Almost every week lacked a detected positive, so this development sample cannot support a claim about forecasting improvements. The official chart-entity crosswalk and a larger release feed are the immediate needs. [Machine-readable summary](../experiments/hit100-musicbrainz-results.json)

## Reproduce

```sh
mkdir -p .forecast
python -m pip install -r requirements.txt duckdb==1.5.4
curl -fL -C - -o .forecast/mbdump-sample.tar.xz https://data.metabrainz.org/pub/musicbrainz/data/sample/20261101-000001/mbdump-sample.tar.xz
curl -fL -o .forecast/hot100-all.json https://raw.githubusercontent.com/mhollingshead/billboard-hot-100/5af164788567600d1565800c2e1bb879c6ef8877/all.json
python -m forecasting.musicbrainz_dump .forecast/mbdump-sample.tar.xz
python -m forecasting.hit100_cohort .forecast/hot100-all.json .forecast/musicbrainz-cohort.json > .forecast/hit100-results.json
```

The tools store row-level release/join outputs and downloaded inputs under the ignored `.forecast` directory. Each run gives hashes for its inputs. The documented chart URL points to the exact Git blob used in the reported run. The replay also caps chart rows at a fixed issue boundary.

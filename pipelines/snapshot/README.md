# Snapshot pipeline

Builds the great-idea sets from the OpenAlex works snapshot (CC0, `s3://openalex`, read
anonymously in `us-east-1`), by the definition in `docs/definitions.md` (10/11/2026, later).

| Step | Script | Output |
|---|---|---|
| Pass 1 | `extract.py`, one call per snapshot file | slim works rows and citation edges |
| Pass 2 | `great.py <dates>` | `great-<T>.parquet`, `summary-<T>.json`, `venues.parquet` |
| Extras | `extras.py` | citations into great ideas, their citing works, every arXiv-posted work |

`job.sh` runs all three on one machine and writes `ALLDONE` only if every step succeeded. Pass 1
is resumable: a file whose done marker exists is skipped.

`tests/test_great.py` runs pass 2 on a synthetic snapshot whose right answers are known: the band,
each home-field rule, the original-paper test, the leak check and the age floor.

Prediction dates: 2008, 2012, 2016, 2020. Citations count only from works published before the
date; ideas must be at least 8 years old at the date.

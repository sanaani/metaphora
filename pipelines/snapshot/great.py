"""Pass 2: the great-idea set at each prediction date, by docs/definitions.md (10/11/2026, later).

    python great.py <pass-1 dir> <arxiv cats parquet> <sources parquet> <out dir> <T> [<T> ...]

Inputs: pass-1 works and edges (extract.py), the arXiv math+stat primary categories (id, cat), and
the snapshot's sources table. Writes <out>/great-<T>.parquet per date, <out>/venues.parquet and
<out>/summary-<T>.json. Every number below is fixed by the definition, not tuned here.
"""

import json
import sys

import duckdb

LO, HI = 1.68, 3.01  # band: top 1 in 48 .. top 1 in 1,023 of subfield-year peers
MIN_AGE = 8  # published at least 8 years before the prediction date
MATH_FIELDS = (26, 18)  # OpenAlex Mathematics, Decision Sciences (rule 3 fallback)
VENUE_MIN_ARXIV = 10  # a venue needs 10 arXiv-posted works to name a home (calibration: >= 10)
CITER_MIN = 5  # rule 4 needs 5 arXiv-posted citers


def main(p1: str, arx: str, src: str, out: str, dates: list[int]) -> None:
    c = duckdb.connect(f"{out}/work.duckdb")
    c.execute("SET memory_limit = '48GB'")
    c.execute(f"SET temp_directory = '{out}/tmp'")
    c.execute(f"CREATE OR REPLACE VIEW works AS SELECT * FROM read_parquet('{p1}/works/*.parquet')")
    c.execute(f"CREATE OR REPLACE VIEW edges AS SELECT * FROM read_parquet('{p1}/edges/*.parquet')")
    c.execute(
        f"CREATE OR REPLACE TABLE arx AS SELECT lower(id) AS arxiv, cat FROM read_parquet('{arx}')"
    )
    c.execute(f"""CREATE OR REPLACE TABLE src AS
        SELECT TRY_CAST(regexp_extract(id, '[0-9]+$') AS BIGINT) AS source, type AS src_type
        FROM read_parquet('{src}')""")
    # Venue facts (all years; a venue's character, not an outcome): field spread, and the share of
    # its arXiv-posted works whose authors chose a math or stat category.
    c.execute("""CREATE OR REPLACE TABLE venues AS
        WITH f AS (SELECT source, field, count(*) AS n FROM works WHERE source IS NOT NULL
                   GROUP BY ALL),
        spread AS (SELECT source, max(n) / sum(n) AS top_field_share, sum(n) AS n_works
                   FROM f GROUP BY source),
        a AS (SELECT w.source, count(*) AS n_arxiv, count(x.cat) AS n_math,
                     mode(x.cat) FILTER (WHERE x.cat IS NOT NULL) AS math_cat
              FROM works w LEFT JOIN arx x USING (arxiv)
              WHERE w.source IS NOT NULL AND w.arxiv IS NOT NULL GROUP BY w.source)
        SELECT s.*, coalesce(a.n_arxiv, 0) AS n_arxiv, coalesce(a.n_math, 0) AS n_math, a.math_cat
        FROM spread s LEFT JOIN a USING (source)""")
    c.execute(f"COPY venues TO '{out}/venues.parquet' (FORMAT parquet)")
    for t in dates:
        one(c, out, t)


def one(c: duckdb.DuckDBPyConnection, out: str, t: int) -> None:
    # Citations received from works published before the prediction date.
    c.execute(f"""CREATE OR REPLACE TABLE pre AS
        SELECT cited AS id, count(*) AS cites_pre FROM edges
        WHERE year < {t} AND cited IS NOT NULL GROUP BY cited""")
    # Rank within subfield and publication year, among all works published before the date.
    c.execute(f"""CREATE OR REPLACE TABLE ranked AS
        SELECT w.*, coalesce(p.cites_pre, 0) AS cites_pre,
               count(*) OVER (PARTITION BY w.subfield, w.year) AS peers,
               rank() OVER (PARTITION BY w.subfield, w.year ORDER BY coalesce(p.cites_pre, 0) DESC)
                 - 1 AS above
        FROM works w LEFT JOIN pre p USING (id)
        WHERE w.year < {t} AND w.subfield IS NOT NULL""")
    c.execute(f"""CREATE OR REPLACE TABLE cand AS
        SELECT r.*, log10(peers / (above + 1)) AS log_n, s.src_type
        FROM ranked r LEFT JOIN src s USING (source)
        WHERE r.year <= {t - MIN_AGE} AND r.cites_pre >= 1 AND log10(peers / (above + 1)) >= {LO}
          AND (log10(peers / (above + 1)) <= {HI}
               OR (r.type = 'article' AND (coalesce(r.refs, 0) >= 1
                   OR (coalesce(r.pages, 0) >= 3 AND s.src_type = 'journal'))))""")
    # Rule 4 input: arXiv-posted citers before the date, and how many chose math or stat.
    c.execute(f"""CREATE OR REPLACE TABLE citers AS
        SELECT e.cited AS id, count(*) AS n_citers, count(x.cat) AS n_math_citers,
               mode(x.cat) FILTER (WHERE x.cat IS NOT NULL) AS citer_cat
        FROM edges e JOIN cand k ON e.cited = k.id
        JOIN works w ON w.id = e.citing
        LEFT JOIN arx x ON x.arxiv = w.arxiv
        WHERE e.year < {t} AND w.arxiv IS NOT NULL GROUP BY e.cited""")
    # Home field, first match wins (definitions.md): own arXiv category; specialized venue;
    # general venue -> own field; arXiv citers; else own field.
    c.execute(f"""CREATE OR REPLACE TABLE great AS
        SELECT k.id, k.year, k.type, k.subfield, k.field, k.source, k.title, k.arxiv, k.cites_pre,
               k.peers, k.above, k.log_n,
               CASE WHEN xa.cat IS NOT NULL THEN 'arxiv'
                    WHEN k.arxiv IS NOT NULL THEN 'arxiv-other'
                    WHEN v.top_field_share >= 0.5 AND v.n_arxiv >= {VENUE_MIN_ARXIV} THEN 'venue'
                    WHEN v.top_field_share < 0.5 THEN 'general-venue'
                    WHEN ci.n_citers >= {CITER_MIN} THEN 'citers'
                    ELSE 'own-field' END AS home_rule,
               CASE WHEN xa.cat IS NOT NULL THEN xa.cat
                    WHEN k.arxiv IS NOT NULL THEN NULL
                    WHEN v.top_field_share >= 0.5 AND v.n_arxiv >= {VENUE_MIN_ARXIV}
                      THEN CASE WHEN v.n_math >= 0.5 * v.n_arxiv THEN v.math_cat END
                    WHEN v.top_field_share < 0.5
                      THEN CASE WHEN k.field IN {MATH_FIELDS} THEN 'field:' || k.field END
                    WHEN ci.n_citers >= {CITER_MIN}
                      THEN CASE WHEN ci.n_math_citers >= 0.5 * ci.n_citers THEN ci.citer_cat END
                    ELSE CASE WHEN k.field IN {MATH_FIELDS} THEN 'field:' || k.field END
               END AS home
        FROM cand k
        LEFT JOIN arx xa ON xa.arxiv = k.arxiv
        LEFT JOIN venues v USING (source)
        LEFT JOIN citers ci USING (id)""")
    c.execute(f"COPY great TO '{out}/great-{t}.parquet' (FORMAT parquet)")
    s = c.execute("""SELECT count(*) AS candidates, count(home) AS in_math_universe,
                            count(*) FILTER (WHERE log_n > 3.01) AS above_max
                     FROM great""").fetchone()
    rules = dict(c.execute("SELECT home_rule, count(home) FROM great GROUP BY 1").fetchall())
    summary = {
        "T": t,
        "candidates": s[0],
        "great_in_math": s[1],
        "above_max": s[2],
        "in_math_by_rule": rules,
    }
    with open(f"{out}/summary-{t}.json", "w") as f:
        json.dump(summary, f, indent=1)
    print(summary, flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:5], [int(x) for x in sys.argv[5:]])

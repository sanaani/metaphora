"""Pass 2: the great-idea set at each prediction date, by docs/definitions.md (10/12/2026).

    python great.py <pass-1 dir> <arxiv cats parquet> <sources parquet> <out dir> <T> [<T> ...]

Inputs: pass-1 works and edges (extract.py), every arXiv paper's primary category (id, cat), and
the snapshot's sources table. Writes <out>/great-<T>.parquet per date, <out>/venues.parquet and
<out>/summary-<T>.json. Every number below is fixed by the definition, not tuned here.
"""

import json
import sys

import duckdb

LO, HI = 1.68, 3.01  # band: top 1 in 48 .. top 1 in 1,023 of subfield-year peers
MIN_AGE = 8  # published at least 8 years before the prediction date
VENUE_MIN = 10  # a journal needs 10 arXiv-posted papers to name a home
CITER_MIN = 5  # the citer rule needs 5 arXiv-posted citers
GROUP = """CASE WHEN cat LIKE 'math%' THEN 'math' WHEN cat LIKE 'stat%' THEN 'stat'
                WHEN cat LIKE 'cs.%' THEN 'cs' WHEN cat LIKE 'q-bio%' THEN 'q-bio'
                WHEN cat LIKE 'q-fin%' THEN 'q-fin' WHEN cat LIKE 'econ%' THEN 'econ'
                WHEN cat LIKE 'eess%' THEN 'eess' ELSE 'physics' END"""
# The math universe: math (math-ph included), stat, or OpenAlex Mathematics / Decision Sciences.
IN_MATH = "(home LIKE 'math%' OR home LIKE 'stat%' OR home IN ('field:26', 'field:18'))"


def home_sql(t: str, citers: bool) -> str:
    """The home rule, first match wins, for rows of table alias t joined to ox (own arXiv
    category), v (venues) and, for ideas, ci (arXiv citers before the date)."""
    rows = [
        ("ox.cat IS NOT NULL", "'arxiv'", "ox.cat"),
        (f"v.n_known >= {VENUE_MIN} AND v.top_group_share >= 0.5", "'venue'", "v.venue_cat"),
        (f"v.n_known >= {VENUE_MIN}", "'general-venue'", f"'field:' || {t}.field"),
    ]
    if citers:
        rows.append((f"ci.n >= {CITER_MIN}", "'citers'", "ci.citer_cat"))
    rule = " ".join(f"WHEN {w} THEN {r}" for w, r, _ in rows)
    home = " ".join(f"WHEN {w} THEN {h}" for w, _, h in rows)
    return (
        f"CASE {rule} ELSE 'own-field' END AS home_rule, "
        f"CASE {home} ELSE 'field:' || {t}.field END AS home"
    )


def main(p1: str, arx: str, src: str, out: str, dates: list[int]) -> None:
    c = duckdb.connect(f"{out}/work.duckdb")
    c.execute("SET memory_limit = '48GB'")
    c.execute(f"SET temp_directory = '{out}/tmp'")
    c.execute(f"CREATE OR REPLACE VIEW works AS SELECT * FROM read_parquet('{p1}/works/*.parquet')")
    c.execute(f"CREATE OR REPLACE VIEW edges AS SELECT * FROM read_parquet('{p1}/edges/*.parquet')")
    c.execute(f"""CREATE OR REPLACE TABLE arx AS
        SELECT lower(id) AS arxiv, cat, {GROUP} AS grp FROM read_parquet('{arx}')""")
    c.execute(f"""CREATE OR REPLACE TABLE src AS
        SELECT TRY_CAST(regexp_extract(id, '[0-9]+$') AS BIGINT) AS source, type AS src_type
        FROM read_parquet('{src}')""")
    # A journal's character, from the categories its authors chose for its arXiv-posted papers.
    c.execute("""CREATE OR REPLACE TABLE venues AS
        WITH a AS (SELECT w.source, x.cat, x.grp FROM works w JOIN arx x USING (arxiv)
                   WHERE w.source IS NOT NULL),
        g AS (SELECT source, grp, count(*) AS n FROM a GROUP BY ALL),
        s AS (SELECT source, sum(n) AS n_known, max(n) / sum(n) AS top_group_share
              FROM g GROUP BY source),
        m AS (SELECT source, mode(cat) AS venue_cat FROM a GROUP BY source)
        SELECT * FROM s JOIN m USING (source)""")
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
    # The citer rule's input: arXiv-posted citers before the date and their commonest category.
    c.execute(f"""CREATE OR REPLACE TABLE ci AS
        SELECT e.cited AS id, count(*) AS n, mode(x.cat) AS citer_cat
        FROM edges e JOIN cand k ON e.cited = k.id
        JOIN works w ON w.id = e.citing
        JOIN arx x ON x.arxiv = w.arxiv
        WHERE e.year < {t} GROUP BY e.cited""")
    c.execute(f"""CREATE OR REPLACE TABLE great AS
        SELECT *, {IN_MATH} AS in_math FROM (
            SELECT k.id, k.year, k.type, k.subfield, k.field, k.source, k.title, k.arxiv,
                   k.cites_pre, k.peers, k.above, k.log_n, {home_sql("k", citers=True)}
            FROM cand k
            LEFT JOIN arx ox ON ox.arxiv = k.arxiv
            LEFT JOIN venues v USING (source)
            LEFT JOIN ci USING (id))""")
    c.execute(f"COPY great TO '{out}/great-{t}.parquet' (FORMAT parquet)")
    s = c.execute("""SELECT count(*), count(*) FILTER (WHERE in_math),
                            count(*) FILTER (WHERE log_n > 3.01) FROM great""").fetchone()
    rules = dict(
        c.execute("SELECT home_rule, count(*) FROM great WHERE in_math GROUP BY 1").fetchall()
    )
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

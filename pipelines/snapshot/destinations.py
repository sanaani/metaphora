"""Pass 3: math destinations. Ideas come from any field; destinations are arXiv math categories.

    python destinations.py <pass-1 dir> <arxiv cats parquet> <out dir> <T> [<T> ...]

Needs pass 2's great-<T>.parquet and venues.parquet in <out>. Writes:

- catmap.parquet: each arXiv category's commonest OpenAlex subfield (the common scale for homes).
- ideas-<T>.parquet: every great idea at T (any field) with home_sub, its home on that scale.
- math-works.parquet: every work whose home (same rule as ideas, without citers) is a math
  category: id, year, dest. These are the destinations' papers.
- math-edges.parquet: every citation from a math work to a great idea at any date:
  citing, year, cited, dest.
- dest-size.parquet: math works per destination and year (how much each area publishes).
"""

import sys

import duckdb
from great import GROUP, home_sql

MATH_DEST = "home LIKE 'math%'"  # arXiv math categories, math-ph included


def main(p1: str, arx: str, out: str, dates: list[int]) -> None:
    c = duckdb.connect(f"{out}/work3.duckdb")
    c.execute("SET memory_limit = '48GB'")
    c.execute(f"SET temp_directory = '{out}/tmp'")
    c.execute(f"CREATE OR REPLACE VIEW works AS SELECT * FROM read_parquet('{p1}/works/*.parquet')")
    c.execute(f"CREATE OR REPLACE VIEW edges AS SELECT * FROM read_parquet('{p1}/edges/*.parquet')")
    c.execute(f"""CREATE OR REPLACE TABLE arx AS
        SELECT lower(id) AS arxiv, cat, {GROUP} AS grp FROM read_parquet('{arx}')""")
    c.execute(f"CREATE OR REPLACE TABLE venues AS SELECT * FROM '{out}/venues.parquet'")
    c.execute("""CREATE OR REPLACE TABLE catmap AS
        SELECT x.cat, mode(w.subfield) AS sub FROM works w JOIN arx x USING (arxiv)
        WHERE w.subfield IS NOT NULL GROUP BY x.cat""")
    c.execute(f"COPY catmap TO '{out}/catmap.parquet' (FORMAT parquet)")
    for t in dates:
        c.execute(f"""COPY (SELECT g.id, g.year, g.type, g.subfield, g.field, g.source, g.title,
                                  g.arxiv, g.cites_pre, g.log_n, g.home_rule, g.home,
                                  CASE WHEN g.home LIKE 'field:%' THEN g.subfield ELSE cm.sub END
                                    AS home_sub
                           FROM '{out}/great-{t}.parquet' g LEFT JOIN catmap cm ON cm.cat = g.home)
                      TO '{out}/ideas-{t}.parquet' (FORMAT parquet)""")
    c.execute(f"""CREATE OR REPLACE TABLE mw AS SELECT id, year, home AS dest FROM (
                    SELECT w.id, w.year, {home_sql("w", citers=False)}
                    FROM works w LEFT JOIN arx ox ON ox.arxiv = w.arxiv
                    LEFT JOIN venues v USING (source)) WHERE {MATH_DEST}""")
    c.execute(f"COPY mw TO '{out}/math-works.parquet' (FORMAT parquet, COMPRESSION zstd)")
    c.execute(f"""CREATE OR REPLACE TABLE cand AS
        SELECT DISTINCT id FROM read_parquet('{out}/great-*.parquet')""")
    c.execute(f"""COPY (SELECT e.citing, e.year, e.cited, m.dest FROM edges e
                       JOIN mw m ON m.id = e.citing SEMI JOIN cand k ON k.id = e.cited)
                  TO '{out}/math-edges.parquet' (FORMAT parquet, COMPRESSION zstd)""")
    c.execute(f"""COPY (SELECT dest, year, count(*) AS n FROM mw GROUP BY ALL)
                  TO '{out}/dest-size.parquet' (FORMAT parquet)""")
    for f in ("math-works", "math-edges"):
        n = c.execute(f"SELECT count(*) FROM '{out}/{f}.parquet'").fetchone()[0]
        print(f, n, flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], [int(x) for x in sys.argv[4:]])

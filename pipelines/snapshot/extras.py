"""Extracts for the steps after "great" (destinations, far, took hold), so the instance can go.

    python extras.py <pass-1 dir> <arxiv cats parquet> <out dir>

great-edges.parquet: every citation (all years) into a work that is great in the math universe at
any date. citing-works.parquet: the slim row and home field of each of those citing works, by the
same rule as ideas (without the citer rule). arxiv-works.parquet: id, source and arXiv id of every
arXiv-posted work.
"""

import sys

import duckdb
from great import GROUP, home_sql


def main(p1: str, arx: str, out: str) -> None:
    c = duckdb.connect(f"{out}/work.duckdb")
    c.execute("SET memory_limit = '48GB'")
    c.execute(f"SET temp_directory = '{out}/tmp'")
    c.execute(f"""CREATE OR REPLACE TABLE arx AS
        SELECT lower(id) AS arxiv, cat, {GROUP} AS grp FROM read_parquet('{arx}')""")
    c.execute(f"CREATE OR REPLACE TABLE venues AS SELECT * FROM '{out}/venues.parquet'")
    c.execute(f"""CREATE OR REPLACE TABLE ideas AS
        SELECT DISTINCT id FROM read_parquet('{out}/great-*.parquet') WHERE in_math""")
    c.execute(f"""COPY (SELECT e.* FROM read_parquet('{p1}/edges/*.parquet') e
                       SEMI JOIN ideas i ON e.cited = i.id)
                  TO '{out}/great-edges.parquet' (FORMAT parquet, COMPRESSION zstd)""")
    c.execute(f"""COPY (SELECT w.id, w.year, w.type, w.subfield, w.field, w.source, w.arxiv,
                              {home_sql("w", citers=False)}
                       FROM read_parquet('{p1}/works/*.parquet') w
                       SEMI JOIN (SELECT DISTINCT citing AS id
                                  FROM read_parquet('{out}/great-edges.parquet')) s USING (id)
                       LEFT JOIN arx ox ON ox.arxiv = w.arxiv
                       LEFT JOIN venues v USING (source))
                  TO '{out}/citing-works.parquet' (FORMAT parquet, COMPRESSION zstd)""")
    c.execute(f"""COPY (SELECT id, source, arxiv FROM read_parquet('{p1}/works/*.parquet')
                       WHERE arxiv IS NOT NULL)
                  TO '{out}/arxiv-works.parquet' (FORMAT parquet, COMPRESSION zstd)""")
    for f in ("great-edges", "citing-works", "arxiv-works"):
        n = c.execute(f"SELECT count(*) FROM read_parquet('{out}/{f}.parquet')").fetchone()[0]
        print(f, n, flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:4])

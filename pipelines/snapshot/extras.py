"""Extracts for the steps after "great" (destinations, far, took hold), so the instance can go.

    python extras.py <pass-1 dir> <out dir>

great-edges.parquet: every citation (all years) into a work that is great in the math universe at
any date. citing-works.parquet: the slim row of each of those citing works. arxiv-works.parquet:
id, source and arXiv id of every arXiv-posted work, so venue homes can use all arXiv categories.
"""

import sys

import duckdb


def main(p1: str, out: str) -> None:
    c = duckdb.connect(f"{out}/work.duckdb")
    c.execute("SET memory_limit = '48GB'")
    c.execute(f"SET temp_directory = '{out}/tmp'")
    c.execute(f"""CREATE OR REPLACE TABLE ideas AS
        SELECT DISTINCT id FROM read_parquet('{out}/great-*.parquet') WHERE home IS NOT NULL""")
    c.execute(f"""COPY (SELECT e.* FROM read_parquet('{p1}/edges/*.parquet') e
                       SEMI JOIN ideas i ON e.cited = i.id)
                  TO '{out}/great-edges.parquet' (FORMAT parquet, COMPRESSION zstd)""")
    c.execute(f"""COPY (SELECT w.id, w.year, w.type, w.subfield, w.field, w.source, w.arxiv
                       FROM read_parquet('{p1}/works/*.parquet') w
                       SEMI JOIN (SELECT DISTINCT citing AS id
                                  FROM read_parquet('{out}/great-edges.parquet')) s USING (id))
                  TO '{out}/citing-works.parquet' (FORMAT parquet, COMPRESSION zstd)""")
    c.execute(f"""COPY (SELECT id, source, arxiv FROM read_parquet('{p1}/works/*.parquet')
                       WHERE arxiv IS NOT NULL)
                  TO '{out}/arxiv-works.parquet' (FORMAT parquet, COMPRESSION zstd)""")
    for f in ("ideas", "great-edges", "citing-works", "arxiv-works"):
        src = "ideas" if f == "ideas" else f"read_parquet('{out}/{f}.parquet')"
        print(f, c.execute(f"SELECT count(*) FROM {src}").fetchone()[0], flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:3])

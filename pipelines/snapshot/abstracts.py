"""Title and abstract text for a given set of works, one snapshot file at a time (resumable).

    python abstracts.py <snapshot parquet> <ids parquet> <out dir> <part name>

OpenAlex stores abstracts as an inverted index (word -> positions); this rebuilds the text in
order. Writes <out>/text/<part>.parquet with (id, text).
"""

import os
import sys

import duckdb


def main(src: str, ids: str, out: str, part: str) -> None:
    done = f"{out}/text-done/{part}"
    if os.path.exists(done):
        return
    for d in ("text", "text-done"):
        os.makedirs(f"{out}/{d}", exist_ok=True)
    c = duckdb.connect()
    c.execute("SET threads TO 2")
    if src.startswith("s3://"):
        c.execute("INSTALL httpfs; LOAD httpfs; SET s3_region = 'us-east-1'")
    c.execute(f"""
        CREATE TABLE w AS
        SELECT TRY_CAST(regexp_extract(id, '[0-9]+$') AS BIGINT) AS id, title,
               abstract_inverted_index AS inv
        FROM read_parquet('{src}')
        SEMI JOIN read_parquet('{ids}') i
          ON i.id = TRY_CAST(regexp_extract(read_parquet.id, '[0-9]+$') AS BIGINT)""")
    c.execute(f"""
        COPY (
          WITH words AS (
            SELECT id, e.key AS word, unnest(e.value) AS pos
            FROM (SELECT id,
                         unnest(map_entries(TRY_CAST(inv::JSON AS MAP(VARCHAR, INTEGER[])))) AS e
                  FROM w WHERE inv IS NOT NULL)),
          abs AS (SELECT id, string_agg(word, ' ' ORDER BY pos) AS abstract FROM words GROUP BY id)
          SELECT w.id, trim(coalesce(w.title, '') || '. ' || coalesce(a.abstract, '')) AS text
          FROM w LEFT JOIN abs a USING (id))
        TO '{out}/text/{part}.parquet' (FORMAT parquet, COMPRESSION zstd)""")
    open(done, "w").close()


if __name__ == "__main__":
    main(*sys.argv[1:5])

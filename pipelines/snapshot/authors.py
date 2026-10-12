"""Author ids for a given set of works, one snapshot file at a time (resumable like extract.py).

    python authors.py <snapshot parquet> <ids parquet> <out dir> <part name>

Writes <out>/authors/<part>.parquet with (id, author) for every listed work in the file.
"""

import os
import sys

import duckdb


def main(src: str, ids: str, out: str, part: str) -> None:
    done = f"{out}/authors-done/{part}"
    if os.path.exists(done):
        return
    for d in ("authors", "authors-done"):
        os.makedirs(f"{out}/{d}", exist_ok=True)
    c = duckdb.connect()
    c.execute("SET threads TO 2")
    if src.startswith("s3://"):
        c.execute("INSTALL httpfs; LOAD httpfs; SET s3_region = 'us-east-1'")
    num = "TRY_CAST(regexp_extract({}, '[0-9]+$') AS BIGINT)"
    c.execute(f"""
        COPY (SELECT w.id, {num.format("a.author.id")} AS author
              FROM (SELECT {num.format("id")} AS id, unnest(authorships) AS a
                    FROM read_parquet('{src}')) w
              SEMI JOIN read_parquet('{ids}') i USING (id))
        TO '{out}/authors/{part}.parquet' (FORMAT parquet, COMPRESSION zstd)""")
    open(done, "w").close()


if __name__ == "__main__":
    main(*sys.argv[1:5])

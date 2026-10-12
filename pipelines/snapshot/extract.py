"""Pass 1 over the OpenAlex works snapshot: one slim works row and the citation edges per file.

    python extract.py <snapshot parquet (local path or s3 url)> <out dir> <part name>

Writes <out>/works/<part>.parquet and <out>/edges/<part>.parquet, then <out>/done/<part>.
A part whose done marker exists is skipped, so a killed run resumes where it stopped.
"""

import os
import sys

import duckdb

W = "https://openalex.org/W"
ARXIV = r"arxiv\.org/(?:abs|pdf)/(.+?)(?:v[0-9]+)?(?:\.pdf)?$|10\.48550/arxiv\.(.+)$"
MATHISH = (26, 18)  # Mathematics, Decision Sciences: keep titles only for these, plus arXiv works


def main(src: str, out: str, part: str) -> None:
    done = f"{out}/done/{part}"
    if os.path.exists(done):
        return
    for d in ("works", "edges", "done"):
        os.makedirs(f"{out}/{d}", exist_ok=True)
    c = duckdb.connect()
    c.execute("SET threads TO 2")
    if src.startswith("s3://"):  # the snapshot bucket is public: anonymous reads, same region
        c.execute("INSTALL httpfs; LOAD httpfs; SET s3_region = 'us-east-1'")
    c.execute(f"CREATE VIEW w AS SELECT * FROM read_parquet('{src}')")
    num = "TRY_CAST(regexp_extract({}, '[0-9]+$') AS BIGINT)"
    arx = (
        "list_filter(list_transform(locations, l -> coalesce("
        f"nullif(regexp_extract(lower(l.landing_page_url), '{ARXIV}', 1), ''),"
        f"nullif(regexp_extract(lower(l.landing_page_url), '{ARXIV}', 2), ''))), x -> x IS NOT NULL)[1]"
    )
    c.execute(f"""
        COPY (SELECT {num.format("id")} AS id, publication_year AS year, type,
                     {num.format("primary_topic.subfield.id")}::INT AS subfield,
                     {num.format("primary_topic.field.id")}::INT AS field,
                     {num.format("primary_location.source.id")} AS source,
                     referenced_works_count AS refs,
                     TRY_CAST(biblio.last_page AS INT) - TRY_CAST(biblio.first_page AS INT) + 1 AS pages,
                     cited_by_count AS cites_now,
                     {arx} AS arxiv,
                     CASE WHEN {num.format("primary_topic.field.id")} IN {MATHISH}
                          OR {arx} IS NOT NULL THEN title END AS title
              FROM w)
        TO '{out}/works/{part}.parquet' (FORMAT parquet, COMPRESSION zstd)""")
    c.execute(f"""
        COPY (SELECT {num.format("id")} AS citing, publication_year AS year,
                     TRY_CAST(substr(r, {len(W) + 1}) AS BIGINT) AS cited
              FROM (SELECT id, publication_year, unnest(referenced_works) AS r FROM w))
        TO '{out}/edges/{part}.parquet' (FORMAT parquet, COMPRESSION zstd)""")
    open(done, "w").close()


if __name__ == "__main__":
    main(*sys.argv[1:4])

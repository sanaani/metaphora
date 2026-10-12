"""The great-idea pass on a synthetic snapshot whose right answers are known by construction."""

import importlib.util
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("great", ROOT / "pipelines/snapshot/great.py")
great = importlib.util.module_from_spec(spec)
spec.loader.exec_module(great)

A, B, LEAK = 2602, 2608, 2603  # subfields: a normal peer group, a big one, a leak check


def work(i, year, subfield, field=26, source=None, arxiv=None, typ="article", refs=5, pages=10):
    return (i, year, typ, subfield, field, source, refs, pages, 0, arxiv, f"w{i}")


def build(tmp: Path) -> None:
    works, edges, arx = [], [], []
    nxt = [10**6]

    def cite(target, n, year=2005, arxiv_cat=None):
        for _ in range(n):
            nxt[0] += 1
            a = f"c{nxt[0]}" if arxiv_cat else None
            if a:
                arx.append((a, arxiv_cat))
            works.append(work(nxt[0], year, None, field=None, arxiv=a))
            edges.append((nxt[0], year, target))

    # Group A: 1,000 peers in 2000; work i gets 100 - i citations for i < 100, so the top 20 pass.
    for i in range(1, 1001):
        src = {3: 501, 4: 502}.get(i)
        arxiv = {1: "math/0001001", 2: "0001.0002"}.get(i)
        field = 31 if i == 6 else 26
        works.append(work(i, 2000, A, field=field, source=src, arxiv=arxiv))
        if i < 100:
            cite(i, 100 - i, arxiv_cat="math.PR" if i == 5 else None)
    arx.append(("math/0001001", "math.AG"))
    # Venue 501: specialized, 12 arXiv-posted math.NT papers. Venue 502: general (5 fields).
    for j in range(12):
        works.append(work(5000 + j, 1990, 9999, source=501, arxiv=f"v{j}"))
        arx.append((f"v{j}", "math.NT"))
    for j in range(20):
        works.append(work(6000 + j, 1990, 9998, field=20 + j % 5, source=502))
    # Group B: 3,000 peers; works 2001 and 2002 are above the max line.
    for i in range(1, 3001):
        typ = "book" if i == 2 else "article"
        works.append(work(2000 + i, 2000, B, typ=typ, refs=0 if i == 2 else 5))
        if i < 200:
            cite(2000 + i, 300 - i)
    # Leak check: a 2000 work whose only citations come after the date, and a 2012 work too young.
    for i in range(1, 101):
        works.append(work(9000 + i, 2000, LEAK))
    cite(9001, 500, year=2020)
    works.append(work(9500, 2012, A))
    cite(9500, 500)
    for d in ("works", "edges"):
        (tmp / "p1" / d).mkdir(parents=True)
    c = duckdb.connect()
    c.execute(
        "CREATE TABLE w (id BIGINT, year INT, type VARCHAR, subfield INT, field INT, source BIGINT,"
        " refs INT, pages INT, cites_now INT, arxiv VARCHAR, title VARCHAR)"
    )
    c.executemany("INSERT INTO w VALUES (?,?,?,?,?,?,?,?,?,?,?)", works)
    c.execute("CREATE TABLE e (citing BIGINT, year INT, cited BIGINT)")
    c.executemany("INSERT INTO e VALUES (?,?,?)", edges)
    c.execute("CREATE TABLE a (id VARCHAR, cat VARCHAR)")
    c.executemany("INSERT INTO a VALUES (?,?)", arx)
    c.execute(f"COPY w TO '{tmp}/p1/works/x.parquet' (FORMAT parquet)")
    c.execute(f"COPY e TO '{tmp}/p1/edges/x.parquet' (FORMAT parquet)")
    c.execute(f"COPY a TO '{tmp}/arx.parquet' (FORMAT parquet)")
    c.execute(f"""COPY (SELECT 'https://openalex.org/S' || s AS id, 'journal' AS type
                  FROM (VALUES (501), (502)) t(s)) TO '{tmp}/src.parquet' (FORMAT parquet)""")


def test_great_pass(tmp_path):
    build(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    great.main(
        str(tmp_path / "p1"),
        str(tmp_path / "arx.parquet"),
        str(tmp_path / "src.parquet"),
        str(out),
        [2016],
    )
    g = {
        r[0]: r[1:]
        for r in duckdb.sql(
            f"SELECT id, home_rule, home FROM '{out}/great-2016.parquet'"
        ).fetchall()
    }
    assert {i for i in g if i < 1001} == set(range(1, 21))  # band: top 1 in 48 of 1,000
    assert g[1] == ("arxiv", "math.AG")
    assert g[2] == ("arxiv-other", None)
    assert g[3] == ("venue", "math.NT")
    assert g[4] == ("general-venue", "field:26")
    assert g[5] == ("citers", "math.PR")
    assert g[6] == ("own-field", None)
    assert g[7] == ("own-field", "field:26")
    assert 2001 in g and 2002 not in g  # above the max line: article kept, book dropped
    assert 9001 not in g  # citations after the date do not count
    assert 9500 not in g  # younger than 8 years at the date

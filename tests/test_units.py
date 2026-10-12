"""Phase 1 units and labels on a hand-built run whose right answers are known."""

import importlib.util
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("units", ROOT / "pipelines/phase1/units.py")
units = importlib.util.module_from_spec(spec)
spec.loader.exec_module(units)


def write(c, rows, cols, path):
    c.execute(f"CREATE OR REPLACE TABLE x ({cols})")
    c.executemany(f"INSERT INTO x VALUES ({','.join('?' * len(cols.split(',')))})", rows)
    c.execute(f"COPY x TO '{path}' (FORMAT parquet)")


def test_units_and_labels(tmp_path):
    c = duckdb.connect()
    write(
        c,
        [(i, 2000, 2602, 50, 2.0) for i in (1, 2, 3)],
        "id BIGINT, year INT, home_sub INT, cites_pre BIGINT, log_n DOUBLE",
        tmp_path / "ideas-2016.parquet",
    )
    edges = [
        (90, 2010, 1, "math.AG"),  # math.AG saw idea 1 before T: 1 citation over 3 ideas = far
        *[(91 + k, 2010, 1 + k % 3, "math.CO") for k in range(5)],  # 5 over 3 ideas: near
        (100, 2017, 2, "math.AG"),  # idea 2 first reaches math.AG in the window
        (101, 2018, 2, "math.AG"),  # later, by other authors
        (102, 2019, 2, "math.AG"),
        (103, 2019, 2, "math.AG"),  # shares an author with the first arrival: excluded
        (104, 2020, 2, "math.AG"),  # shares an author with the idea: excluded
        (105, 2022, 2, "math.AG"),  # after the 4-year uptake window: not counted
        (110, 2020, 3, "math.AG"),  # idea 3 arrives after the 3-year arrival window
    ]
    write(
        c,
        edges,
        "citing BIGINT, year INT, cited BIGINT, dest VARCHAR",
        tmp_path / "math-edges.parquet",
    )
    write(
        c,
        [("math.AG", 2014, 10), ("math.CO", 2014, 20)],
        "dest VARCHAR, year INT, n BIGINT",
        tmp_path / "dest-size.parquet",
    )
    authors = [(2, 1), (104, 1), (100, 2), (103, 2), (101, 3), (102, 4), (105, 5), (110, 6)]
    write(c, authors, "id BIGINT, author BIGINT", tmp_path / "authors.parquet")
    units.main(str(tmp_path), 2016, str(tmp_path / "out"))
    u = {
        (r[0], r[1]): r[2:]
        for r in duckdb.sql(
            f"SELECT id, dest, arrived, later_others FROM '{tmp_path}/out/units-2016.parquet'"
        ).fetchall()
    }
    assert (1, "math.AG") not in u  # already cited there before T
    assert not any(d == "math.CO" for _, d in u)  # near for this home
    assert u[(2, "math.AG")] == (True, 2)
    assert u[(3, "math.AG")] == (False, 0)

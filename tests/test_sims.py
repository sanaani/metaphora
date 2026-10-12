"""Destination profiles and idea similarities on hand-made embeddings."""

import importlib.util
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sims", ROOT / "pipelines/phase1/sims.py")
sims = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sims)


def test_sims(tmp_path):
    (tmp_path / "phase1").mkdir()
    # Works 1-2 are math.AG papers along x, 3 a math.CO paper along y, 4 a math.AG paper from
    # outside the profile years; ideas 10 (along x), 11 (along y), 12 (no text).
    ids = np.array([1, 2, 3, 4, 10, 11], dtype=np.int64)
    e = np.array([[1, 0], [1, 0], [0, 1], [0, 1], [1, 0], [0, 1]], dtype=np.float16)
    np.save(tmp_path / "emb-ids.npy", ids)
    np.save(tmp_path / "emb.npy", e)
    c = duckdb.connect()
    c.execute(f"""COPY (SELECT * FROM (VALUES (1, 2013, 'math.AG'), (2, 2015, 'math.AG'),
                         (3, 2014, 'math.CO'), (4, 2010, 'math.AG')) t(id, year, dest))
                  TO '{tmp_path}/math-works.parquet' (FORMAT parquet)""")
    c.execute(f"""COPY (SELECT * FROM (VALUES (10), (11), (12)) t(id))
                  TO '{tmp_path}/ideas-2016.parquet' (FORMAT parquet)""")
    sims.main(str(tmp_path), str(tmp_path), 2016)
    s = {
        (r[0], r[1]): r[2]
        for r in duckdb.sql(
            f"SELECT id, dest, sim FROM '{tmp_path}/phase1/sims-2016.parquet'"
        ).fetchall()
    }
    assert abs(s[(10, "math.AG")] - 1) < 1e-3 and abs(s[(10, "math.CO")]) < 1e-3
    assert abs(s[(11, "math.CO")] - 1) < 1e-3
    assert (12, "math.AG") not in s  # no text, no similarity

"""The phase 1 verdict code on synthetic units where the right verdicts are known."""

import importlib.util
import json
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("evaluate", ROOT / "pipelines/phase1/evaluate.py")
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)


def make(run: Path, text_matters: bool) -> None:
    (run / "phase1").mkdir(parents=True)
    rng = np.random.default_rng(1)
    for t in (2002, 2009, 2016):
        n_ideas, dests = 3000, ["math.AG", "math.CO", "math.PR"]
        ids = np.repeat(np.arange(n_ideas) + 10 * t, len(dests))
        dest = np.tile(np.array(dests, dtype=object), n_ideas)
        n = len(ids)
        cites = rng.lognormal(3, 1, n)
        sim = rng.normal(0, 1, n)
        z = -5 + 0.8 * np.log1p(cites) + (1.5 * sim if text_matters else 0)
        y = rng.random(n) < 1 / (1 + np.exp(-z))
        c = duckdb.connect()
        c.register(
            "u",
            {
                "id": ids,
                "dest": dest.astype(str),
                "habit": rng.random(n) * 0.5,
                "dest_size": np.full(n, 100.0),
                "cites_pre": cites,
                "age": np.full(n, 10),
                "math_breadth": np.zeros(n),
                "math_recent": np.zeros(n),
                "home_sub": np.full(n, 2602),
                "arrived": y,
                "later_others": np.where(y, 3, 0),
            },
        )
        c.execute(f"COPY u TO '{run}/phase1/units-{t}.parquet' (FORMAT parquet)")
        c.register("s", {"id": ids, "dest": dest.astype(str), "sim": sim.astype(np.float32)})
        c.execute(f"COPY s TO '{run}/phase1/sims-{t}.parquet' (FORMAT parquet)")


def test_text_signal_passes_h2(tmp_path):
    make(tmp_path, text_matters=True)
    ev.main(str(tmp_path), 2002, 2009, 2016)
    v = json.loads((tmp_path / "phase1/verdicts.json").read_text())
    assert v["H1"] == "PASS"  # citations predict, habit is noise here
    assert v["H2"] == "PASS"
    assert v["precision_at_k"]["text"] > v["precision_at_k"]["baseline"]


def test_no_text_signal_fails_h2(tmp_path):
    make(tmp_path, text_matters=False)
    ev.main(str(tmp_path), 2002, 2009, 2016)
    v = json.loads((tmp_path / "phase1/verdicts.json").read_text())
    assert v["H2"] == "FAIL"

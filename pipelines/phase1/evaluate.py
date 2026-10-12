"""Phase 1 verdicts, by the rules in README.md. Run once.

    python evaluate.py <run dir> [<dates: train tune test>]

Fits the baseline and text models on the training date, takes each destination's k from the
tuning date, ranks every unit at the test date, and applies H1 and H2 with 95% bootstrap intervals
that resample ideas (Poisson weights, 1,000 replicates).
"""

import json
import sys

import duckdb
import numpy as np
from sklearn.linear_model import LogisticRegression

LINE = 2  # took hold: at least 2 later citations by other authors (fitted on T = 2002)
NEG_RATE = 0.02  # training keeps every positive and this share of negatives, reweighted
TOP = 5000  # ranked units kept per destination and model; k is far smaller
B, SEED = 1000, 20261012
BASE = [
    "ln(1+habit)",
    "ln(1+dest_size)",
    "ln(1+cites_pre)",
    "age",
    "ln(1+math_breadth)",
    "ln(1+math_recent)",
]


def feats(alias: str = "") -> str:
    a = f"{alias}." if alias else ""
    return ", ".join(
        [
            f"ln(1 + {a}habit)",
            f"ln(1 + {a}dest_size)",
            f"ln(1 + {a}cites_pre)",
            f"{a}age",
            f"ln(1 + {a}math_breadth)",
            f"ln(1 + {a}math_recent)",
        ]
    )


def load(c, run: str, t: int) -> None:
    c.execute(f"""CREATE OR REPLACE VIEW u{t} AS
        SELECT u.*, (u.arrived AND u.later_others >= {LINE}) AS y, s.sim
        FROM '{run}/phase1/units-{t}.parquet' u
        LEFT JOIN '{run}/phase1/sims-{t}.parquet' s USING (id, dest)""")


def fit(c, t: int):
    q = f"""SELECT {feats()}, sim, y FROM u{t}
            WHERE y OR hash(id, dest) % 1000 < {int(NEG_RATE * 1000)}"""
    d = c.execute(q).fetchnumpy()
    y = d["y"].astype(int)
    xb = np.column_stack([d[k] for k in list(d)[:6]]).astype(float)
    sim = d["sim"].astype(float)
    fill = np.nanmean(sim)
    xt = np.column_stack([xb, np.where(np.isnan(sim), fill, sim)])
    w = np.where(y == 1, 1.0, 1 / NEG_RATE)
    models = {}
    for name, x in (("baseline", xb), ("text", xt)):
        mu, sd = x.mean(0), x.std(0)
        sd = np.where(sd < 1e-6, 1.0, sd)  # a constant feature stays unscaled
        m = LogisticRegression(max_iter=2000).fit((x - mu) / sd, y, sample_weight=w)
        coef = m.coef_[0] / sd
        b0 = float(m.intercept_[0] - (coef * mu).sum())
        models[name] = (b0, [float(v) for v in coef], float(fill))
    return models, int(y.sum())


def score_sql(model, with_text: bool) -> str:
    b0, coef, fill = model
    terms = [f"({coef[i]!r}) * ({f})" for i, f in enumerate(feats().split(", "))]
    if with_text:
        terms.append(f"({coef[6]!r}) * coalesce(sim, {fill!r})")
    return f"{b0!r} + " + " + ".join(terms)


def main(run: str, train: int, tune: int, test: int) -> None:
    c = duckdb.connect()
    c.execute("SET memory_limit = '48GB'")
    for t in (train, tune, test):
        load(c, run, t)
    models, npos = fit(c, train)
    ks = dict(
        c.execute(f"SELECT dest, count(*) FILTER (WHERE y) FROM u{tune} GROUP BY 1").fetchall()
    )
    c.execute(
        "CREATE TABLE k AS SELECT * FROM (VALUES "
        + ", ".join(f"('{d}', {n})" for d, n in ks.items())
        + ") t(dest, k)"
    )
    scores = {
        "habit": "habit + 1e-9 * (hash(id, dest) % 1000000)",  # ties broken at random, fixed seed
        "baseline": score_sql(models["baseline"], False),
        "text": score_sql(models["text"], True),
    }
    tops = {}
    for name, s in scores.items():
        tops[name] = c.execute(f"""
            SELECT dest, id, y::INT AS y FROM (
                SELECT dest, id, y, row_number() OVER (PARTITION BY dest ORDER BY {s} DESC) AS r
                FROM u{test}) WHERE r <= {TOP} ORDER BY dest, r""").fetchnumpy()
    kk = {d: n for d, n in ks.items() if n > 0}
    ideas = np.unique(np.concatenate([tops[m]["id"] for m in tops]))

    def prec(top, wt):
        hits = tot = 0.0
        for d, k in kk.items():
            sel = top["dest"] == d
            ids, y = top["id"][sel], top["y"][sel]
            ww = np.ones(len(ids)) if wt is None else wt[np.searchsorted(ideas, ids)]
            cum = np.cumsum(ww)
            take = np.clip(k - (cum - ww), 0, ww)  # weight of each unit inside the top k
            hits += (take * y).sum()
            tot += k
        return hits / tot

    point = {m: prec(tops[m], None) for m in tops}
    rng = np.random.default_rng(SEED)
    reps = {m: [] for m in tops}
    for _ in range(B):
        wt = rng.poisson(1.0, len(ideas)).astype(float)
        for m, top in tops.items():
            reps[m].append(prec(top, wt))
    reps = {m: np.array(v) for m, v in reps.items()}

    def ci(a):
        return [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]

    h1 = reps["baseline"] - reps["habit"]
    h2 = reps["text"] - reps["baseline"]
    out = {
        "train_positives": npos,
        "destinations_with_k": len(kk),
        "total_k": int(sum(kk.values())),
        "precision_at_k": point,
        "precision_ci": {m: ci(reps[m]) for m in reps},
        "H1_baseline_minus_habit": {"point": point["baseline"] - point["habit"], "ci": ci(h1)},
        "H2_text_minus_baseline": {"point": point["text"] - point["baseline"], "ci": ci(h2)},
    }
    out["H1"] = "PASS" if out["H1_baseline_minus_habit"]["ci"][0] > 0 else "FAIL"
    out["H2"] = "PASS" if out["H2_text_minus_baseline"]["ci"][0] > 0 else "FAIL"
    out["coefficients"] = {m: [float(x) for x in models[m][1]] for m in models}
    out["features"] = BASE + ["sim"]
    with open(f"{run}/phase1/verdicts.json", "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    dates = [int(x) for x in sys.argv[2:5]] or [2002, 2009, 2016]
    main(sys.argv[1], *dates)

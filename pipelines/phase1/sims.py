"""Similarity between each idea and each destination at a date T.

    python sims.py <run dir> <emb dir> <T>

A destination's profile is the mean of its papers' embeddings from the 3 years before T. Writes
<run>/phase1/sims-<T>.parquet with (id, dest, sim): the cosine between the idea and the profile.
"""

import sys

import duckdb
import numpy as np


def rows_of(ids_sorted: np.ndarray, want: np.ndarray) -> np.ndarray:
    """Row of each wanted id in the sorted embedding ids, or -1 when it has no text."""
    k = np.searchsorted(ids_sorted, want)
    k[k == len(ids_sorted)] = 0
    return np.where(ids_sorted[k] == want, k, -1)


def main(run: str, emb: str, t: int) -> None:
    ids = np.load(f"{emb}/emb-ids.npy")  # sorted by embed.py
    e = np.load(f"{emb}/emb.npy").astype(np.float32)
    mw = duckdb.sql(f"""SELECT id, dest FROM '{run}/math-works.parquet'
                        WHERE year BETWEEN {t - 3} AND {t - 1}""").fetchnumpy()
    dests, dj = np.unique(mw["dest"], return_inverse=True)
    r = rows_of(ids, mw["id"].astype(np.int64))
    prof = np.zeros((len(dests), e.shape[1]), np.float32)
    np.add.at(prof, dj[r >= 0], e[r[r >= 0]])
    prof /= np.maximum(np.linalg.norm(prof, axis=1, keepdims=True), 1e-12)
    idea = duckdb.sql(f"SELECT id FROM '{run}/ideas-{t}.parquet'").fetchnumpy()["id"]
    ri = rows_of(ids, idea.astype(np.int64))
    idea, ri = idea[ri >= 0], ri[ri >= 0]
    s = e[ri] @ prof.T
    c = duckdb.connect()
    c.register("d", {"j": np.arange(len(dests), dtype=np.int32), "dest": dests.astype(str)})
    c.register(
        "s",
        {
            "id": np.repeat(idea, len(dests)),
            "j": np.tile(np.arange(len(dests), dtype=np.int32), len(idea)),
            "sim": s.reshape(-1).astype(np.float32),
        },
    )
    c.execute(f"""COPY (SELECT s.id, d.dest, s.sim FROM s JOIN d USING (j))
                  TO '{run}/phase1/sims-{t}.parquet' (FORMAT parquet, COMPRESSION zstd)""")
    print(t, "ideas with text", len(idea), "destinations", len(dests), flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]))

"""Encode every idea and destination paper with a fixed pretrained sentence encoder (GPU).

    python embed.py <text parquet> <out dir>

Model: BAAI/bge-small-en-v1.5, no fine-tuning, inputs cut at 256 tokens, unit-normalized outputs.
Writes <out>/emb-ids.npy (int64) and <out>/emb.npy (float16), in chunks so a killed run resumes.
"""

import os
import sys

import duckdb
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL, MAX_LEN, CHUNK = "BAAI/bge-small-en-v1.5", 256, 200_000


def main(text: str, out: str) -> None:
    os.makedirs(f"{out}/chunks", exist_ok=True)
    rows = duckdb.sql(f"SELECT id, text FROM '{text}' ORDER BY id").fetchnumpy()
    ids, texts = rows["id"].astype(np.int64), rows["text"]
    model = SentenceTransformer(MODEL, device="cuda")
    model.max_seq_length = MAX_LEN
    model.half()
    n = (len(ids) + CHUNK - 1) // CHUNK
    for k in range(n):
        f = f"{out}/chunks/{k:04d}.npy"
        if os.path.exists(f):
            continue
        part = [str(x) for x in texts[k * CHUNK : (k + 1) * CHUNK]]
        e = model.encode(part, batch_size=512, normalize_embeddings=True, show_progress_bar=False)
        np.save(f + ".tmp.npy", e.astype(np.float16))
        os.replace(f + ".tmp.npy", f)
        print(f"chunk {k + 1}/{n}", flush=True)
    np.save(f"{out}/emb-ids.npy", ids)
    np.save(
        f"{out}/emb.npy", np.concatenate([np.load(f"{out}/chunks/{k:04d}.npy") for k in range(n)])
    )


if __name__ == "__main__":
    main(*sys.argv[1:3])

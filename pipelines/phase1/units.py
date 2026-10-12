"""Units, labels and baseline features for one prediction date T.

    python units.py <run dir> <T> [<out dir>]

Unit: (idea, destination) where the idea is great at T (any field), the destination is an arXiv
math category that is far for the idea's home, and no work in that destination cited the idea
before T.

Far: a destination is far for a home if, before T, the home's great ideas received on average
fewer than one citation each from it (definitions.md).

Outcome: whether the idea first reaches the destination in [T, T + ARRIVE), and how many more works
there cite it within UPTAKE years after that arrival, counting only works sharing no author with
the idea or with the first arrival (later_others). The took-hold line is applied afterwards.
ARRIVE + UPTAKE = 7, so the window for T = 2016 ends in 2023, the last year with complete
references (math articles: 79% have references in 2023, 69% in 2024).

Features, all from data before T: the home's habit of reaching the destination, the destination's
size, the idea's citations, its age, how many math categories already cite it, and its citations
from math in the 3 years before T.
"""

import os
import sys

import duckdb

ARRIVE, UPTAKE = 3, 4


def main(run: str, t: int, out: str) -> None:
    os.makedirs(out, exist_ok=True)
    c = duckdb.connect()
    c.execute("SET memory_limit = '48GB'")
    c.execute(f"SET temp_directory = '{out}/tmp'")
    c.execute(f"CREATE VIEW me AS SELECT * FROM '{run}/math-edges.parquet'")
    # An idea whose home fell back to its own OpenAlex label (no arXiv, journal or citer evidence)
    # takes its home from its math citers instead when at least half of its citations before T,
    # and at least 5, come from math papers whose category is known: OpenAlex labels old works
    # badly (Bredon's topology textbook is filed under high-energy physics).
    c.execute(f"""CREATE TABLE mc AS SELECT cited AS id, count(*) AS n, mode(dest) AS dest
                  FROM me WHERE year < {t} GROUP BY 1""")
    c.execute(f"""CREATE TABLE ideas AS
        SELECT i.id, i.year, i.cites_pre, i.log_n,
               CASE WHEN i.home_rule = 'own-field' AND mc.n >= 5 AND mc.n >= 0.5 * i.cites_pre
                    THEN cm.sub ELSE i.home_sub END AS home_sub
        FROM '{run}/ideas-{t}.parquet' i LEFT JOIN mc USING (id)
        LEFT JOIN '{run}/catmap.parquet' cm ON cm.cat = mc.dest""")
    c.execute("DELETE FROM ideas WHERE home_sub IS NULL")
    # The home's habit: average citations per great idea from each math destination before T.
    c.execute(f"""CREATE TABLE habit AS
        WITH n AS (SELECT home_sub, count(*) AS ideas FROM ideas GROUP BY 1),
        x AS (SELECT i.home_sub, e.dest, count(*) AS cites FROM me e JOIN ideas i ON i.id = e.cited
              WHERE e.year < {t} GROUP BY ALL)
        SELECT n.home_sub, d.dest, coalesce(x.cites, 0) / n.ideas AS habit
        FROM n CROSS JOIN (SELECT DISTINCT dest FROM me) d
        LEFT JOIN x ON x.home_sub = n.home_sub AND x.dest = d.dest""")
    c.execute(f"""CREATE TABLE size AS SELECT dest, sum(n) AS dest_size
                  FROM '{run}/dest-size.parquet' WHERE year BETWEEN {t - 3} AND {t - 1} GROUP BY 1""")
    c.execute(f"""CREATE TABLE pre AS SELECT cited AS id, count(DISTINCT dest) AS math_breadth,
                         count(*) FILTER (WHERE year >= {t - 3}) AS math_recent
                  FROM me WHERE year < {t} GROUP BY 1""")
    c.execute(
        f"""CREATE TABLE seen AS SELECT DISTINCT cited AS id, dest FROM me WHERE year < {t}"""
    )
    c.execute(f"""CREATE TABLE units AS
        SELECT i.id, h.dest, h.habit, coalesce(s.dest_size, 0) AS dest_size, i.cites_pre,
               {t} - i.year AS age, coalesce(p.math_breadth, 0) AS math_breadth,
               coalesce(p.math_recent, 0) AS math_recent, i.home_sub
        FROM ideas i JOIN habit h USING (home_sub)
        LEFT JOIN size s USING (dest) LEFT JOIN pre p USING (id)
        WHERE h.habit < 1
          AND NOT EXISTS (SELECT 1 FROM seen x WHERE x.id = i.id AND x.dest = h.dest)""")
    # Labels: first arrival in the window, then uptake by other authors.
    c.execute(f"""CREATE TABLE arr AS
        SELECT e.cited AS id, e.dest, min(e.year) AS a FROM me e
        SEMI JOIN units u ON u.id = e.cited AND u.dest = e.dest
        WHERE e.year >= {t} GROUP BY ALL HAVING min(e.year) < {t + ARRIVE}""")
    c.execute(f"CREATE TABLE au AS SELECT * FROM '{run}/authors.parquet'")
    c.execute("""CREATE TABLE excl AS
        SELECT r.id, r.dest, a.author FROM arr r JOIN au a ON a.id = r.id
        UNION SELECT r.id, r.dest, a.author FROM arr r
              JOIN me e ON e.cited = r.id AND e.dest = r.dest AND e.year = r.a
              JOIN au a ON a.id = e.citing""")
    c.execute(f"""CREATE TABLE later AS
        SELECT r.id, r.dest, count(DISTINCT e.citing) AS n FROM arr r
        JOIN me e ON e.cited = r.id AND e.dest = r.dest AND e.year > r.a AND e.year <= r.a + {UPTAKE}
        WHERE NOT EXISTS (SELECT 1 FROM au a JOIN excl x ON x.author = a.author
                          WHERE a.id = e.citing AND x.id = r.id AND x.dest = r.dest)
        GROUP BY ALL""")
    c.execute(f"""COPY (SELECT u.*, (r.a IS NOT NULL) AS arrived,
                              coalesce(l.n, 0) AS later_others
                       FROM units u LEFT JOIN arr r USING (id, dest) LEFT JOIN later l USING (id, dest))
                  TO '{out}/units-{t}.parquet' (FORMAT parquet, COMPRESSION zstd)""")
    print(
        c.sql(f"""SELECT count(*) AS units, count(DISTINCT id) AS ideas,
                           count(*) FILTER (WHERE arrived) AS arrived,
                           count(*) FILTER (WHERE later_others >= 3) AS later3
                    FROM '{out}/units-{t}.parquet'""")
    )


if __name__ == "__main__":
    run, t = sys.argv[1], int(sys.argv[2])
    main(run, t, sys.argv[3] if len(sys.argv) > 3 else f"{run}/phase1")

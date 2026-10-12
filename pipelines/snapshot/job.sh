#!/bin/bash
# Runs on the instance. Pass 1 over every works file, the sources table, pass 2 (great ideas),
# pass 3 (math destinations), author lists for every idea and math citing work, then sha256 sums.
# Writes /data/logs/ALLDONE only if every step succeeded. Pass 1 and the author pass resume.
set -euo pipefail
D=/data; cd ~/job; mkdir -p $D/logs $D/p1 $D/out
log() { echo "$(date -u +%H:%M:%S) $*" | tee -a $D/logs/job.log; }
PY=~/venv/bin/python
ARX=arxiv-cats.parquet
DATES="2002 2009 2016"  # train, tune, test: each outcome window (7 years) ends before the next date
per_file() {  # per_file <script> <extra args...>: run a resumable per-file script over the snapshot
  local s=$1; shift
  nl -v0 files.txt | xargs -P 8 -L 1 bash -c 'p=$(printf "part_%04d" $0); '"$PY $s"' "$1" '"$*"' $p || echo "FAIL $p" >> '"$D/logs/fail-$s.txt"
  if [ -s "$D/logs/fail-$s.txt" ]; then mv "$D/logs/fail-$s.txt" "$D/logs/fail1-$s.txt"
    nl -v0 files.txt | xargs -P 4 -L 1 bash -c 'p=$(printf "part_%04d" $0); '"$PY $s"' "$1" '"$*"' $p || echo "FAIL $p" >> '"$D/logs/fail-$s.txt"; fi
  [ ! -s "$D/logs/fail-$s.txt" ] || { log "$s FAILED"; exit 1; }
}
log "pass 1: $(wc -l < files.txt) files"
per_file extract.py $D/p1
[ "$(ls $D/p1/done | wc -l)" -eq "$(wc -l < files.txt)" ] || { log "pass 1 incomplete"; exit 1; }
$PY -c "
import duckdb; c = duckdb.connect(); c.execute(\"INSTALL httpfs; LOAD httpfs; SET s3_region='us-east-1'\")
c.execute(\"COPY (SELECT id, type FROM read_parquet('s3://openalex/data/parquet/sources/*/*.parquet', union_by_name=true)) TO '$D/sources.parquet' (FORMAT parquet)\")"
log "pass 1 and sources done"
$PY great.py $D/p1 $ARX $D/sources.parquet $D/out $DATES 2>&1 | tee -a $D/logs/job.log
$PY destinations.py $D/p1 $ARX $D/out $DATES 2>&1 | tee -a $D/logs/job.log
log "passes 2 and 3 done"
$PY -c "
import duckdb
duckdb.sql(\"COPY (SELECT id FROM read_parquet('$D/out/ideas-*.parquet') UNION SELECT DISTINCT citing FROM '$D/out/math-edges.parquet') TO '$D/author-ids.parquet' (FORMAT parquet)\")"
per_file authors.py $D/author-ids.parquet $D/a
$PY -c "import duckdb; duckdb.sql(\"COPY (SELECT DISTINCT * FROM read_parquet('$D/a/authors/*.parquet') WHERE author IS NOT NULL) TO '$D/out/authors.parquet' (FORMAT parquet, COMPRESSION zstd)\")"
log "authors done"
cd $D/out && sha256sum great-*.parquet ideas-*.parquet summary-*.json venues.parquet catmap.parquet math-works.parquet math-edges.parquet dest-size.parquet authors.parquet > SHA256SUMS
log "ALL STEPS OK"; echo ALLDONE > $D/logs/ALLDONE

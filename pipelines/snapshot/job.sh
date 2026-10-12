#!/bin/bash
# Runs on the instance. Pass 1 over every works file, the sources table, pass 2, the extracts the
# later steps need, then sha256 sums. Writes /data/logs/ALLDONE only if every step succeeded.
set -euo pipefail
D=/data; cd ~/job; mkdir -p $D/logs $D/p1 $D/out
log() { echo "$(date -u +%H:%M:%S) $*" | tee -a $D/logs/job.log; }
PY=~/venv/bin/python
ARX=arxiv-cats.parquet
log "pass 1: $(wc -l < files.txt) files"
nl -v0 files.txt | xargs -P 8 -L 1 bash -c 'p=$(printf "part_%04d" $0); '"$PY"' extract.py "$1" '"$D"'/p1 $p || echo "FAIL $p $1" >> '"$D"'/logs/fail.txt'
[ ! -s $D/logs/fail.txt ] || { log "retrying failures"; mv $D/logs/fail.txt $D/logs/fail1.txt
  nl -v0 files.txt | xargs -P 4 -L 1 bash -c 'p=$(printf "part_%04d" $0); '"$PY"' extract.py "$1" '"$D"'/p1 $p || echo "FAIL $p $1" >> '"$D"'/logs/fail.txt'; }
[ ! -s $D/logs/fail.txt ] || { log "pass 1 FAILED: $(wc -l < $D/logs/fail.txt) files"; exit 1; }
[ "$(ls $D/p1/done | wc -l)" -eq "$(wc -l < files.txt)" ] || { log "pass 1 incomplete"; exit 1; }
log "pass 1 done: $(du -sh $D/p1 | cut -f1)"
$PY -c "
import duckdb; c = duckdb.connect(); c.execute(\"INSTALL httpfs; LOAD httpfs; SET s3_region='us-east-1'\")
c.execute(\"COPY (SELECT id, type FROM read_parquet('s3://openalex/data/parquet/sources/*/*.parquet', union_by_name=true)) TO '$D/sources.parquet' (FORMAT parquet)\")"
log "sources done"
$PY great.py $D/p1 $ARX $D/sources.parquet $D/out 2008 2012 2016 2020 2>&1 | tee -a $D/logs/job.log
log "pass 2 done"
$PY extras.py $D/p1 $ARX $D/out 2>&1 | tee -a $D/logs/job.log
log "extras done"
cd $D/out && sha256sum great-*.parquet summary-*.json venues.parquet great-edges.parquet citing-works.parquet arxiv-works.parquet > SHA256SUMS
log "ALL STEPS OK"; echo ALLDONE > $D/logs/ALLDONE

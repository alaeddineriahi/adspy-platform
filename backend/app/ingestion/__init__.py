"""
Self-serve ad ingestion.

Pulls ads from Meta's public Ad Library (scraper), keeps only the
best-performing ones (long-running + scaling + genuine e-commerce), and indexes
them into Elasticsearch — on a schedule and/or on demand.

Modules:
- scraper.py   : low-level Meta Ad Library client (HTTP + cookie auth + parsing)
- scoring.py   : best-performing scorer + e-commerce spam filter
- pipeline.py  : orchestration (fetch -> score -> filter -> dedup -> upsert)
- scheduler.py : autonomous periodic runs
"""

# Data policy

This repository is public. Everything committed is published, and git history keeps it after
deletion. These rules exist so nothing sensitive is ever committed.

## What may be used

| Source | License | May be committed |
|---|---|---|
| OpenAlex works, citations, topics | CC0 | Aggregates and IDs only, under 2 MB per file |
| arXiv metadata (titles, abstracts, categories) | CC0 | Aggregates and IDs only |
| arXiv full text | per paper; most use arXiv's non-exclusive license | No. Process locally; commit only derived numbers |
| Mathlib (Lean) | Apache-2.0 | Yes, with attribution |
| Anything else | must be checked and recorded here **before** it is downloaded | — |

## What is never used

- Client data, or any company-internal data: messages, transcripts, documents, repositories,
  usage logs.
- Private communications of any kind, including public email corpora.
- Data whose license forbids redistribution or is unknown.
- Personal data beyond what a public bibliographic record already holds (author names and IDs).

## Where things live

- Code, write-ups and small aggregate results: this repo.
- Raw data, models and outputs: `~/metaphora-data`, never in the repo. `.gitignore` blocks the
  common data formats as a second line of defense.
- Credentials: environment variables or files under `~/metaphora-data` or `~/.config`. Code reads
  them at run time and never prints, logs or writes them. Never put a key in a URL that is
  logged.

## How it is enforced

`scripts/check-leaks.sh` runs at commit (staged changes), at push (every tracked file) and in CI
(every tracked file and all history):

1. **gitleaks**, with its default rules plus `.gitleaks.toml`, for credentials of every common
   shape. Install it once: download the release for your platform from
   <https://github.com/gitleaks/gitleaks/releases>, verify its checksum, and put the binary on
   `PATH` or in `~/metaphora-data/tools/`.
2. **A private deny-list** of client, company and personal terms, and any key values, matched
   case-insensitively on word boundaries. It lives at `~/.config/metaphora/denylist.txt` (or
   `$METAPHORA_DENYLIST`) and in the `METAPHORA_DENYLIST` Actions secret, never in the repo,
   because listing those terms in a public file would itself leak them. A match prints a count,
   never the term.
3. **A 2 MB cap** on every tracked file, so no dataset slips in.

GitHub secret scanning with push protection is also on for the repository.

If a check fires on something harmless (a common word that is also on the list), reword it. Do
not weaken the check. If anything sensitive is ever pushed, treat it as public: rotate the
credential first, then clean the history.

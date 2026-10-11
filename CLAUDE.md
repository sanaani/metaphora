# Metaphora: rules for agents

- **This repo is public.** Read `docs/data-policy.md` before adding any data. Never commit client
  or company data, private communications, credentials, or any file over 2 MB. Raw data lives in
  `~/metaphora-data`.
- Never print, log or paste a credential, and never put one in a committed file or a logged URL.
- Never add deny-listed terms to the repo, including in docs that explain the deny-list.
- Hooks live in `.githooks` (`git config core.hooksPath .githooks`). Pre-commit runs
  `scripts/check-leaks.sh staged` and lint; pre-push runs the leak check on every tracked file,
  lint and pytest. Never bypass them with `--no-verify`.
- Lint with `scripts/lint.sh` (`--fix` formats). Line length is 100.
- After every push, confirm CI with `gh run list --limit 1`. A red run is fixed before any other
  work.
- Hypotheses are fixed in a phase README and approved before any outcome is looked at. Real
  outcomes only: no LLM grading.
- US English; dates as MM/DD/YYYY in prose, ISO in filenames.

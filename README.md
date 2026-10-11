# Metaphora

**Where will a great idea be used next, far from where it came from?**

*Metaphora* (μεταφορά) is Greek for "a carrying across." This project studies one kind of
carrying across: a high-impact idea from one field being put to work in a distant one, as when
Gelfand settled questions in functional analysis with ring theory's maximal ideals, or when
Montgomery's formula for the zeros of the zeta function turned out to match the statistics of
energy levels in heavy nuclei.

## Goal

**Predict where a great existing idea will be used next, especially far from where it came
from.** Connecting ideas is not the point; connecting great ones is.

- **Great idea:** a work of high impact, judged only from evidence that existed before the
  prediction date. Never judged by an LLM.
- **Transfer:** the first time an area that never used the idea uses it.
- **Took hold:** the new area keeps using it in the years after. This is the outcome that
  counts, so a passing mention does not.
- **Far:** the two areas rarely drew on each other before the date.
- **Success:** using only data up to a date, the transfers that later take hold rank above those
  that do not, beating citation count alone, with a top of the list worth a researcher's time.
- **Out of scope:** producing new ideas from nothing, and predicting links between ideas of any
  weight.

## Where it comes from

Metaphora combines two earlier projects:

- [**Noema**](https://github.com/sanaani/noema) asked whether the shape of Lean proofs predicts
  which theorems connect. On Mathlib the signal was real but weak, and Mathlib records when
  mathematics was formalized, not when a connection was made. Its arXiv phases found the
  stronger result: the text of the papers already using a popular work predicts which new area
  will cite it (AUC 0.813 → 0.870), and its 15-year watch found cold jumps that took hold.
- [**Dianoia**](https://github.com/sanaani/dianoia) trained an encoder to find *far* analogies,
  ones with no shared vocabulary. On patents it lifted far-analogy retrieval from 52.6% to 77.7%
  top-10, and the gain carried to management papers it never saw (20% → 36.5%).

Metaphora asks Noema's question of data that holds real, dated transfers (scholarly citations
through [OpenAlex](https://openalex.org), CC0), with Dianoia's far-analogy encoder as a
candidate method.

## Status

Set up 10/11/2026. Nothing has been run. Every test is pre-registered in its phase README before
any outcome is looked at.

## Working here

- Data policy: [`docs/data-policy.md`](docs/data-policy.md). Read it before adding any data.
- Enable the hooks once: `git config core.hooksPath .githooks`. Pre-commit checks staged changes
  for leaks and lints; pre-push checks every tracked file and runs the tests. Never bypass them.
- License: Apache-2.0 for code. Data keeps its source's license and is not committed.

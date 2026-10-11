# Definitions (provisional)

Decisions made before any data is scored. Each one is dated; a definition changes only by a new
dated entry, never by editing an old one.

## 10/11/2026

**Home field and destination come from the authors.** A work's field is the arXiv primary
category its authors chose, not a database's topic label. OpenAlex topic labels were checked on a
sample and are often wrong: Riemann's 1854 lecture is filed under theoretical computer science,
and neuroscience papers under statistics. A work that predates arXiv takes as its home the arXiv
category that cited it most up to the prediction date.

**Every field is judged against its own habit of traveling.** Fields differ in how far their ideas
usually go: a statistics method reaching biology is routine; a topology result reaching biology is
not. So:

- **Far** is relative to the home field: a destination is far for an idea only if ideas from that
  home field rarely reached it before the prediction date.
- **Baselines know each field's travel rate,** so a model cannot win by betting on fields that
  travel.
- **Scoring is within each home field:** an idea is ranked only against ideas from the same home
  field.

Statistics is therefore included, held to its own bar.

**"Great" is not yet defined.** A sample of 250 OpenAlex works showed that raw citation count
selects statistics procedures, textbooks, handbooks and software, while plainly great mathematics
has modest counts (Riemann 1854: 349 citations). Working hypothesis, to be calibrated against
human-curated lists of seminal papers before it is fixed:

1. an original research work, not a textbook, handbook, survey or software package;
2. high impact for its own home field and age (percentile within field and year);
3. lasting: still cited decades later;
4. never judged by an LLM.

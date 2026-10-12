# Phase 1: where will great ideas take hold in mathematics?

Fixed 10/12/2026, before any outcome at the tuning or test date was looked at. Changes to this file
after that point are new dated sections, never edits.

## Question

Given the great ideas at a prediction date T, from any field, which areas of mathematics, far from
each idea's home, will take them up? A mathematician values learning that a great idea from
elsewhere (physics, computer science, a distant part of mathematics) is about to take hold in their
own area, so the destinations are mathematics only: arXiv's math categories.

## Definitions (docs/definitions.md)

- **Great idea at T:** the filter of 10/11-10/12/2026, any field, using only citations before T.
- **Home:** the home rule; on the OpenAlex subfield scale (an arXiv category becomes the subfield
  its arXiv papers most often carry).
- **Destination:** an arXiv math category (math-ph included); a work's category comes from the same
  home rule as ideas, without the citer rule.
- **Far:** before T, the home's great ideas received on average fewer than one citation each from
  the destination.
- **Unit:** (idea, destination) with the destination far for the idea's home and no citation of the
  idea from the destination before T.
- **Took hold:** first citation from the destination within 3 years of T, then at least L more
  within 4 years of that arrival from works sharing no author with the idea or the first arrival.
  L is the smallest count at which a two-population fit (one-off arrivals vs sustained uptake) on
  the training date's arrivals makes sustained uptake the likelier source. It is fitted once, on
  T = 2002 only, and then fixed.

## Dates

Train T = 2002, tune T = 2009, test T = 2016, used once. Each outcome window (3 + 4 years) ends
before the next date: 2009, 2016, 2023. 2023 is the last year with complete references (math
articles with references: 79% in 2023, 69% in 2024, 56% in 2025), so the test window is complete.
Features use only data before their date.

## Models

- **Habit:** rank by the home's average citations per idea from the destination (the field's own
  travel rate).
- **Baseline:** logistic regression on habit, destination size (its papers in the 3 years before
  T), the idea's citations, age, number of math categories already citing it, and its math
  citations in the 3 years before T (counts log-transformed). Fit on T = 2002.
- **Text (method under test):** the baseline plus the cosine similarity between the idea's title
  and abstract and the centroid of the destination's papers from the 3 years before T, from a
  pretrained general-purpose sentence encoder (no fine-tuning). Fit on T = 2002. The encoder and
  any setting are chosen on T = 2009 only.

## Measure

For each destination, rank its units and take the top k, where k is the number of units that took
hold there at the tuning date (T = 2009). Precision at k is total hits over total k, across all
destinations. Uncertainty: 95% bootstrap intervals, resampling ideas.

## Hypotheses (test date only)

- **H1 (the outcome is learnable):** the baseline beats habit alone; the lower end of the 95%
  interval of the precision difference is above 0.
- **H2 (the method):** text beats the baseline; the lower end of the 95% interval of the precision
  difference is above 0.

Real outcomes only; no LLM judges anything.

## 10/12/2026: took-hold line fitted on T = 2002

Later citations by other authors after the 22,805 first arrivals at T = 2002 (counts 0 to 5:
18,453 / 2,786 / 817 / 348 / 163 / 91, and 147 at 6 or more) fit one-off arrivals (84%, mean 0.13
later citations) and sustained uptake (16%, mean 1.46). Sustained uptake is the likelier source from
2 later citations (69%; 30% at 1). **L = 2**, fixed: 1,566 of the 2002 arrivals (6.9%) took hold.

Units: 41.5 million at T = 2002, 57.1 million at 2009, 85.4 million at 2016. The script that built
them printed the count of arrivals and of three-or-more uptakes at every date, including the test
date. No model, line or setting has been or will be chosen with it; from here on the tuning and
test outcomes are read only by the scripts that apply the pre-written rules.

## 10/12/2026: units rebuilt

Ideas whose home fell back to OpenAlex's own label take it from their math citers when at least half
of their citations before T (and at least 5) come from math papers of known category. Units were
rebuilt; the rebuild again printed arrival and three-or-more counts at every date, because an edit
removing that printout had failed. The printout is now gone (units.py prints unit and idea counts
only). Nothing has been chosen with those counts.

## 10/12/2026: results (test date 2016, run once)

Verdicts in `verdicts.json`, from `evaluate.py` as pre-written. 31 math categories had took-hold
events at the tuning date, so k totals 3,061 test picks. At T = 2016, 3,985 of 85.4 million units
took hold: 1 in 21,400.

| Ranking | Precision at k | 95% interval |
|---|---:|---|
| Habit (the home's travel rate) | 0.03% | 0.00% to 0.13% |
| Baseline | 4.70% | 3.92% to 5.46% |
| Baseline + text | 4.67% | 3.92% to 5.42% |

- **H1 passes.** The baseline beats habit by 4.67 points (95% interval 3.92 to 5.42); its picks
  take hold about 1,000 times more often than chance. Most of its weight is on the idea's recent
  citations from mathematics and on the home's habit.
- **H2 fails.** Text similarity adds nothing (-0.03 points, interval -0.33 to +0.33), although it
  carried weight in training.

What the top picks look like: a mix of general tools crossing math areas (ridge regression and
robust estimation into functional analysis, sliced inverse regression into numerical analysis) and
genuine cross-area uptake (tensor eigenvalues into mathematical physics, chemotaxis PDE models into
classical analysis).

**Limits found:**
- 43% of ideas have a title but no abstract in OpenAlex, which weakens the text test.
- A destination can come from the journal's commonest arXiv category, so every paper in a broad
  journal gets one label (an optimization method "taken up" in combinatorics).
- Textbooks pass the band and travel as ideas (*Algebraic Geometry* into general topology).

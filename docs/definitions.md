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

## 10/11/2026, later: "great" and the home field

Calibrated against 72 human-curated seminal works (Steele Prize seminal-contribution papers and
Wikipedia's lists of important publications in mathematics and statistics), 359 ordinary works and
360 most-cited works from the same subfields and years. All counts are from OpenAlex.

**Home field.** This replaces the pre-arXiv rule above. The category that cites a work most is
where the work went, not where it came from: Choi's paper on completely positive maps, published in
a linear algebra journal, comes out as quantum physics. The home is the first of:

1. the arXiv primary category its authors chose, if the work is on arXiv;
2. if its journal is specialized (one field publishes at least half of the journal's works), the
   most common arXiv primary category among that journal's arXiv-posted papers;
3. if its journal is general (such as *PNAS* or *Nature*), the work's own OpenAlex field;
4. otherwise, the most common arXiv primary category among works citing it before the
   prediction date.

This puts 64 of the 72 curated works in mathematics or statistics; most of the other 8 have another
home in fact (Shannon in information theory, von Neumann and Morgenstern in economics).

**A great idea** is a work that passes all of:

1. **Peers:** ranked against works of the same OpenAlex subfield and publication year. Ranking by
   subfield separates curated from ordinary works as well as ranking by field does (AUC 0.956
   vs 0.954), and better than ranking by topic (0.88).
2. **Pre-date evidence only:** rank counts only citations from works published before the
   prediction date.
3. **Age:** published at least 8 years before the prediction date. Of the works a young paper's
   rank flags, the share still flagged 13 years on is 47% at age 1, 65% at age 3, 75% at age 5 and
   87% at age 8. The curve has no knee, so 8 is a judgment call. It costs little: 92% of the
   citations a curated work receives from other fields arrive after age 8.
4. **Band:** between the top 1 in 48 and the top 1 in 1,023 of its peers. Both lines are where the
   density of curated works crosses the density of ordinary and of most-cited works. The band holds
   71% of curated works, 7% of ordinary and 30% of most-cited.
5. **Above the band, original papers only:** a journal article with at least one reference, or at
   least 3 pages in a journal. OpenAlex files many textbooks as articles: they are one-page book
   reviews that carry the book's citations. This test cuts the most-cited works above the band from
   69% to 54% of the group and loses one curated work. Inside the band it is not applied, because
   curated lists include seminal books.

**Tested and dropped:**

- **Disruption index** (CD over 5 years): AUC 0.50 against ordinary works, 0.35 against most-cited.
- **Journal prestige:** works in five flagship journals are 25% of curated works and 2% of the
  others, but adding a journal's track record to early citation rank changes nothing (AUC 0.915 to
  0.926 at age 1, identical from age 3). Reported as a feature, not used as a filter.
- **Merging duplicate records** (reprints, translations): curated works passing the lower line
  stay at 66 of 72, and 8 more ordinary works pass. Not worth it.

**Known limit:** the filter flags about 2% of cited works, more than anyone would call great.
Without a large-scale human judgment of greatness, no sharper objective cut was found.

**Running it:** the free API budget (about $1 a day) is far too small, so the production filter runs
on the OpenAlex snapshot. The arXiv categories come from arXiv's OAI-PMH service.

## 10/12/2026: home field, as built on the snapshot

Running the definition on the OpenAlex snapshot (release of 09/23/2026) exposed three problems,
each fixed in `pipelines/snapshot` with a synthetic test:

1. **OpenAlex subject labels differ between releases.** The live API filed Daubechies' wavelet
   paper under applied mathematics; the snapshot files it under computer vision. So a journal is no
   longer judged by OpenAlex fields alone. A journal is specialized when at least half of its
   arXiv-posted papers share one arXiv group, and its home is their most common category.
2. **Only some fields post to arXiv** (mathematics 19% of papers since 2007, physics 12%, medicine
   0.3%), so a general journal's arXiv sample is mostly physics (*Nature* 97%, *Science* 98%). Two
   witnesses must therefore agree: the journal's commonest OpenAlex field must be one that arXiv
   papers of its majority group carry more often than arXiv papers overall. *Nature*, *Science*,
   *PLoS ONE* and *Scientific Reports* (commonest field: medicine) count as general; *PNAS*
   (biochemistry) still passes as physics, a known error. Control and numerical journals whose
   commonest OpenAlex field is engineering (*IEEE Transactions on Automatic Control*, *Journal of
   Computational Physics*) also count as general, for the same reason: their arXiv samples
   over-represent the mathematicians who publish there. Their papers can still be mathematics by
   their own field.
3. **Only edited venues have a character.** Journals, conferences and book series can name a home;
   ebook platforms and repositories cannot (an ebook platform's arXiv-posted books are mostly math).
   The math universe takes OpenAlex Decision Sciences only for its operations research and
   statistics subfields, not Information Systems and Management.

On the calibration set (works published by 2008, at T = 2016), 47 of 68 curated works are great
ideas in the math universe, against 27 of 337 ordinary and 103 of 337 most-cited works. Great ideas
in the math universe: 46,155 (T = 2008), 56,808 (2012), 72,456 (2016), 92,458 (2020).

**Proposed, awaiting approval: far and took hold.** Homes and destinations are put on one scale,
OpenAlex subfields; an arXiv category becomes the subfield its arXiv papers most often carry.

- **Far:** a destination is far for a home if a typical great idea from that home would expect
  less than one citation from it before the date: (destination's share of the home's citations)
  times (the home's median citations per great idea) is below 1. Before 2016 this leaves each math
  home 20 to 40 near subfields; far subfields supplied 10% to 38% of its citations.
- **Took hold:** after first reaching a far destination, at least 4 more citations from it within
  5 years. Later citations after 355,762 first far arrivals (2000 to 2010) fit two populations:
  one-off arrivals (87%, mean 0.45 later citations) and sustained uptake (13%, mean 5.2). Four is
  the smallest count at which sustained uptake is the likelier source (65%; 40% at 3). About 7% of
  far arrivals took hold. Self-citation is not yet excluded.

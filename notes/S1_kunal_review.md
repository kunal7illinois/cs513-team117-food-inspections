# S1 - Kunal's review of U1 and dataset description

Per the Phase-I plan, S1 is an independent review pass by each team member of the
use case (U1) and dataset description before profiling/cleaning starts. This is
my pass; Zehra and Che-Min should add their own notes below or in a separate file.

## What I checked

- Re-read Section 1 (dataset description) and Section 2a (U1) of the Phase-I report.
- Cross-checked the Violations-column claims specifically, since that's my S2/S3
  ownership: "About 72 percent of rows have something in the Violations field"
  and "usually lists somewhere between 4 and 5 separate violations."

## Findings

Both claims hold up against the full 298,869-row file:
- 27.89% of rows have a blank Violations field (i.e. 72.11% have content) - matches.
- Median violation count per non-blank row is in the 3-5 range - matches
  ("4 and 5" as a typical range is accurate; see S2 profiling notes for the full
  distribution).

U1 ("Which violations drive failures, by facility type and ZIP over time?") and
the four documented DQ problems still hold. No changes needed to the use case or
dataset description based on this review. The one addition worth folding into
the Phase-II report: we now have an exact count of distinct raw violation codes
(65) and confirmed the pre/post-2018 code collision empirically (see S2 notes) -
Phase-I only asserted this qualitatively with two examples.

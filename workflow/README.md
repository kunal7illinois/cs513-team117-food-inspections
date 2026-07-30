# Workflow model

- **`Workflow_W1_outer.dot`** / `.png` / `.pdf` - the outer workflow: the whole
  pipeline from the raw CSV through the three parallel S3 cleaning
  workstreams, the join (S3), before/after validation (S4), and the change
  summary (S5).
- **`Workflow_W2_inner.dot`** / `.png` / `.pdf` - the inner OpenRefine
  workflow behind `facility_type_lookup.csv` and `city_lookup.csv`, grouped
  from the 115 raw operations in `../openrefine/OpenRefine.json` into stages
  (add column -> text-transform -> cluster/mass-edit -> export -> dedupe).

The single-diagram versions above are wide (long left-to-right chains), which
prints too small to read on a normal page. For the actual report body, each
diagram is also split into legible parts, same content, same source data,
just broken at natural stage boundaries and rendered bigger:

- `Workflow_W1_outer_part1.*` (raw CSV -> S3 cleaning -> join),
  `Workflow_W1_outer_part2a.*` (join outputs -> before/after queries),
  `Workflow_W1_outer_part2b.*` (change summary -> report)
- `Workflow_W2_inner_part1.*` (OpenRefine clustering, both lanes),
  `Workflow_W2_inner_part2.*` (export -> dedupe/reshape)

Dashed boxes at the start/end of each part ("continued from Part N" / "continued
in Part N") mark where the parts connect. The report embeds these part images
on landscape pages; the single-file versions are kept as the compact overview.

Built with Graphviz (same tool as the Phase-I ER diagram in
`Phase1-Section1-Artifacts/`), not the OR2YW tool mentioned in the
assignment - OR2YW would generate W2 directly from the OpenRefine JSON, but
requires installing that separate tool; this version was built by parsing
the same JSON file by hand instead. Re-render either with:

```
dot -Tpng Workflow_W1_outer.dot -o Workflow_W1_outer.png
dot -Tpdf Workflow_W1_outer.dot -o Workflow_W1_outer.pdf
```

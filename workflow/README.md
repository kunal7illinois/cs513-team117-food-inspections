# Workflow model

- **`Workflow_W1_outer.dot`** / `.png` / `.pdf` - the outer workflow: the whole
  pipeline from the raw CSV through the three parallel S3 cleaning
  workstreams, the join (S3), before/after validation (S4), and the change
  summary (S5).
- **`Workflow_W2_inner.dot`** / `.png` / `.pdf` - the inner OpenRefine
  workflow behind `facility_type_lookup.csv` and `city_lookup.csv`, grouped
  from the 115 raw operations in `../openrefine/OpenRefine.json` into stages
  (add column -> text-transform -> cluster/mass-edit -> export -> dedupe).

Built with Graphviz (same tool as the Phase-I ER diagram in
`Phase1-Section1-Artifacts/`), not the OR2YW tool mentioned in the
assignment - OR2YW would generate W2 directly from the OpenRefine JSON, but
requires installing that separate tool; this version was built by parsing
the same JSON file by hand instead. Re-render either with:

```
dot -Tpng Workflow_W1_outer.dot -o Workflow_W1_outer.png
dot -Tpdf Workflow_W1_outer.dot -o Workflow_W1_outer.pdf
```

---
name: ontogpt-extract
description: >-
  Batch-run `ontogpt extract` over many input files against one LinkML schema
  and one LLM (local Ollama or paid cloud), in parallel; then reconcile
  duplicate ungrounded (AUTO:) entities across the files and enrich the merged
  result with labels, definitions and is-a ancestors from the source ontologies
  (FOODON / UO / RO / CHEBI / ...). Use when the user wants to extract an
  ontology from several documents at once, or mentions ontogpt batch / parallel
  extraction, AUTO duplicate reconciliation, or ontology enrichment.
---

# OntoGPT batch extract → reconcile → enrich

Turn a folder of documents into one clean, enriched ontology in three stages:

```
            ┌──────────────┐   parallel, one job per file
  inputs ─▶ │ 1. EXTRACT   │ ─────────────────────────────▶  one .owl per input
            └──────────────┘   ontogpt extract (schema + LLM)
            ┌──────────────┐   merge all files into one graph, then collapse
  .owl  ─▶  │ 2. RECONCILE │ ─────────────────────────────▶  reconciled.owl
            └──────────────┘   AUTO duplicates → canonical / grounded IRIs
            ┌──────────────┐   pull labels, defs & is-a ancestors of the
  recon ─▶  │ 3. ENRICH    │ ─────────────────────────────▶  final.owl
            └──────────────┘   grounded terms; ROBOT merge
```

**Why reconcile before enrich?** When SPIRES grounding fails, ontogpt mints a
placeholder IRI in the `AUTO:` namespace from the entity's label. Across files
the same thing surfaces under different AUTO IRIs because the label was written
differently — `Soy Lecithin` vs `Soy lecithin`, `Fudge Mint Cookie` vs
`Fudge Mint Cookies` — or it grounded in one file but not another (`Cocoa` →
`FOODON:03301072` here, `AUTO:Cocoa` there). Each variant becomes its own class.
Stage 2 fixes this **once all files are processed**: it folds AUTO variants
together and, crucially, folds AUTO entities into the real grounded term when
their labels match. Enriching afterwards means the source-ontology lookups run
on the de-duplicated set.

## Scripts (in `scripts/` next to this file)

| Script | Stage |
| --- | --- |
| `extract_parallel.sh` | 1 — parallel `ontogpt extract` over many files |
| `reconcile_auto.py` | 2 — `plan` then `apply` AUTO de-duplication |
| `enrich_ontology.sh` | 3 — auto-detect grounded ontologies, enrich, ROBOT merge |

Run each with `--help` for full options.

## Prerequisites

- `ontogpt` and `runoak` on PATH (the project venv — `command -v ontogpt`
  should resolve). `reconcile_auto.py` needs that venv's Python for `rdflib`.
- GNU `parallel` (`brew install parallel`).
- `ROBOT` + a Java runtime for enrichment (`brew install robot`).
- **Cloud model** → the API key exported (e.g. `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`).
- **Local model** → Ollama running (`ollama serve`) and the model pulled
  (`ollama pull <model>`).
- Inputs must be **text** files. Convert PDFs/HTML to `.txt` first.

## How to run it

First resolve the helper paths once (works regardless of cwd):

```bash
SKILL="$(cd "$(dirname "${BASH_SOURCE:-$0}")" && pwd)"   # or hard-code the scripts dir
SKILL=".../.claude/skills/ontogpt-extract/scripts"        # the scripts directory
VENV_PY="$(dirname "$(command -v ontogpt)")/python"       # venv python (has rdflib)
OUT="ontogpt-out"                                         # output root
```

### Gather from the user (ask only for what's missing)
- **Input files** — a glob or explicit list (e.g. `data/*.txt`).
- **Schema** — path to a LinkML `.yaml`, or a packaged template name (`recipe.Recipe`).
- **Model** — e.g. `ollama/gemma4:26b` (local) or `gpt-4o` / `claude-3-5-sonnet-latest` (cloud).
- (Optional) concurrency, output dir.

### Stage 1 — Extract in parallel

```bash
"$SKILL/extract_parallel.sh" \
  --schema grocery-item.yaml \
  --model  ollama/gemma4:26b \
  --out    "$OUT/extractions" \
  data/*.txt
```

Produces one `.owl` per input in `$OUT/extractions/`, plus `parallel.joblog`
and per-file logs under `logs/`. It keeps going if a file fails and reports the
count; check the logs for any failures before continuing.

**Concurrency (`--jobs`).** Defaults: **4** for cloud models, **2** for
`ollama/*`. Tune by model type:
- *Cloud APIs* scale well — raise `--jobs` for speed, but watch provider **rate
  limits** (429s show up in the per-file logs; lower `--jobs` if you see them).
- *Local Ollama* is one server. Extra jobs only help if `OLLAMA_NUM_PARALLEL`
  and your RAM/VRAM allow concurrent requests; otherwise they queue and can
  thrash memory. Each file already triggers many sequential LLM calls (SPIRES
  recursion), so start at 1–2 and raise only if the machine has headroom.

### Stage 2 — Reconcile AUTO duplicates

**Plan first** (writes a review TSV, changes nothing):

```bash
"$VENV_PY" "$SKILL/reconcile_auto.py" plan \
  -i "$OUT"/extractions/*.owl \
  -o "$OUT/reconcile-map.tsv"
```

It prints the proposed merges, e.g.

```
[ground] canonical: Cocoa  <.../FOODON_03301072>
    ==> 'Cocoa'  <http://example.org/auto/Cocoa>
[dedup]  canonical: Soy Lecithin  <.../auto/Soy%20Lecithin>
    -->  'Soy lecithin'  <.../auto/Soy%20lecithin>
```

**Review the merges with the user when any are non-trivial** — reconciliation
can over-merge. The `reconcile-map.tsv` is a plain `old_iri → new_iri` table;
the user can delete or edit rows before applying. Default matching folds only
case / whitespace / punctuation differences (safe). Add `--fold-plurals` to also
merge regular singular/plural pairs (`cookies`≈`cookie`) — handier but riskier,
so always review its output. `ground-CONFLICT` rows (an AUTO label matching more
than one grounded term) are flagged for manual resolution.

**Then apply** (merges all inputs into one graph and rewrites the duplicates):

```bash
"$VENV_PY" "$SKILL/reconcile_auto.py" apply \
  -i "$OUT"/extractions/*.owl \
  --map "$OUT/reconcile-map.tsv" \
  -o "$OUT/reconciled.owl"
```

The canonical pick prefers a Title-Case, shortest surface form (singular over
plural); grounded terms always win over AUTO ones. Each surviving entity keeps a
single canonical label.

### Stage 3 — Enrich from the source ontologies

```bash
"$SKILL/enrich_ontology.sh" \
  --input "$OUT/reconciled.owl" \
  --out   "$OUT/final.owl"
```

It auto-detects which ontologies were grounded against (by scanning the IRIs),
and for each one collects the grounded CURIEs, expands them to is-a ancestors
with `runoak`, extracts that subset as OBO (labels + definitions + `is_a`), then
ROBOT-merges everything into `final.owl`. This is the generalised, written-on-
the-fly form of the hand-coded enrichment snippet — it adapts to whatever
ontologies appear, instead of hard-coding `FOODON/UO/RO`.

- Each prefix defaults to the OAK adapter `sqlite:obo:<lowercase-prefix>`.
  Override or group prefixes with `--adapters "BFO=sqlite:obo:ro,RO=sqlite:obo:ro"`.
- Restrict to specific ontologies with `--only "FOODON UO"`.
- The first `runoak` call for an ontology downloads its SQLite DB (large/slow);
  later runs use the cache.

### Report back
Tell the user: how many files succeeded/failed, how many duplicate entities were
folded (and notably any AUTO→grounded folds), which ontologies were enriched,
and the path to `final.owl`.

## Output layout

```
ontogpt-out/
├── extractions/         one .owl per input + logs/ + parallel.joblog
├── reconcile-map.tsv    proposed AUTO merges (review/edit before apply)
├── reconciled.owl       merged + de-duplicated ontology
├── tmp-enrich/          per-ontology OBO subsets (intermediate)
└── final.owl            enriched final ontology
```

## Troubleshooting

- **`ontogpt`/`runoak` not found** → activate the project venv; they live in
  `.venv/bin`. `VENV_PY` derives from `command -v ontogpt`, so resolve that first.
- **rdflib ImportError** → you ran `reconcile_auto.py` with the wrong Python;
  use `"$VENV_PY"`.
- **A file fails in stage 1** → see `extractions/logs/<name>/stderr` and the
  joblog. Common causes: missing API key, Ollama not running / model not pulled,
  rate limits (lower `--jobs`).
- **Nothing to reconcile** → no duplicate labels across files; skip to enrich.
- **Enrich finds no prefixes** → the extraction grounded nothing (all `AUTO:`);
  `final.owl` is just the reconciled input. Improve the schema's `annotators:`
  or the prompt, or pick a stronger model.
- **`robot` errors** → ensure Java is installed and on PATH.

## Reference: the original hand-written enrichment

`enrich_ontology.sh` generalises this snippet from the demo README (kept here so
the manual steps are visible). For a single known set of ontologies you could
run it directly instead:

```bash
mkdir -p tmp
grep -oE "(FOODON|UO|BFO|RO)_[0-9]+" input.owl | sort -u | sed 's/_/:/' > tmp/grounded-ids.txt
grep -E "^FOODON:"   tmp/grounded-ids.txt > tmp/foodon-ids.txt
grep -E "^UO:"       tmp/grounded-ids.txt > tmp/uo-ids.txt
grep -E "^(BFO|RO):" tmp/grounded-ids.txt > tmp/ro-ids.txt
for prefix in foodon uo ro; do
  runoak -i sqlite:obo:$prefix ancestors -p i .idfile tmp/${prefix}-ids.txt \
    --output-type csv 2>/dev/null | awk -F'\t' 'NR>1 && $1 ~ /:/{print $1}' | sort -u \
    > tmp/${prefix}-anc.txt
  cat tmp/${prefix}-ids.txt >> tmp/${prefix}-anc.txt
  sort -u -o tmp/${prefix}-anc.txt tmp/${prefix}-anc.txt
  runoak -i sqlite:obo:$prefix extract .idfile tmp/${prefix}-anc.txt --dangling -p i \
    -O obo -o tmp/${prefix}-enriched.obo
done
robot merge --input input.owl \
  --input tmp/foodon-enriched.obo --input tmp/uo-enriched.obo --input tmp/ro-enriched.obo \
  --output input.enriched.owl
```

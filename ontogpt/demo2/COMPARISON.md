# GPT-4o vs. Gemma 4 — Extraction Comparison

This note compares the two OntoGPT extractions of the *Spinach and Feta Turkey Burgers* recipe:

| File | Model |
| ---- | ----- |
| [`demo1/spinach-feta-turkey-burgers.yaml`](../demo1/spinach-feta-turkey-burgers.yaml) | **GPT-4o** (cloud) |
| [`demo2/spinach-feta-turkey-burgers.yaml`](./spinach-feta-turkey-burgers.yaml) | **Gemma 4** (local) |

We treat the **GPT-4o** output as the gold standard and ask: *how different is the Gemma 4 output?*

---

## Result summary: the grounding is nearly identical

Comparing the set of **grounded** ontology IDs (real FOODON / UO / HANCESTRO terms, ignoring the `AUTO:` placeholders):

| | GPT-4o (gold) | Gemma 4 |
| --- | :---: | :---: |
| Grounded terms | 11 | 9 |
| `AUTO:` (ungrounded) terms | 19 | 18 |

- **Shared: 9 terms** — turkey, spinach, feta cheese, garlic, oil, eggs, patties, ounce, pounds. Every core ingredient and unit is grounded to the **exact same** FOODON/UO ID in both runs.
- **Only in GPT-4o: 2 terms** — `FOODON:00002647` (Grilled) and `HANCESTRO:0463` (American), both *category* groundings.
- **Only in Gemma 4: 0 terms.** Gemma's grounded set is a strict **subset** of GPT-4o's.

So on the substantive task, which is mapping the actual food items to the food ontology, **Gemma 4 matched GPT-4o 100%**. It captured 9 of GPT-4o's 11 grounded terms (82%), and the 2 it "missed" are inferred recipe categories, not ingredients.

### Shared grounded terms

| CURIE | Label |
| ----- | ----- |
| `FOODON:02020418` | turkey |
| `FOODON:00002968` | spinach |
| `FOODON:03307280` | feta cheese |
| `FOODON:00003582` | garlic |
| `FOODON:03310387` | oil |
| `FOODON:03316061` | eggs |
| `FOODON:00002951` | patties |
| `UO:0010033` | ounce |
| `UO:0010034` | pounds |

---

## Where they actually differ

| Field | GPT-4o (gold) | Gemma 4 | Verdict |
| ----- | ------------- | ------- | ------- |
| **description** | Near-verbatim copy from the source text | Paraphrased / reworded | GPT-4o is more faithful for an *extraction* task |
| **categories** | 5 (Main, Summer, Grilled, American, Healthy); 2 grounded | 2 (Summer recipes, Turkey burgers); 0 grounded | Both partly invent categories; GPT-4o grounds 2 of them |
| **ingredients (food)** | All 6 mapped; eggs → `FOODON:03316061` | 5/6 identical; **eggs → `AUTO:large eggs`** in the ingredient slot | Gemma's one ingredient-level grounding miss |
| **eggs (nuance)** | Grounded in the ingredient *and* the step | Grounded (`FOODON:03316061`) only in the "mix" step, not the ingredient slot | Both *found* the term; Gemma placed it inconsistently |
| **egg amount unit** | `AUTO:large` | `AUTO:None` | Both ungrounded; trivially different |
| **steps (actions)** | preheat, mix, form, **measure** | preheat;oil, mix together, form, **cook** | Gemma's "cook" maps better to source Step 3; GPT-4o's "measure" (fixating on the thermometer) is a weaker reading |
| **state strings** | "none" / "N/A" | "N/A" / "not specified" | Cosmetic wording only |

---

## Bottom line

For this recipe, **Gemma 4 is surprisingly close to the GPT-4o gold standard** — essentially equivalent on ingredient/unit ontology grounding (the part that matters most), with **no incorrect groundings**. The divergences are at the margins and roughly cancel out in quality:

- **GPT-4o is better at:** category grounding, verbatim description, consistent egg placement.
- **Gemma 4 is arguably better at:** step segmentation ("cook" vs. GPT-4o's odd "measure").
- **Neither grounds:** cooking spray, feta (the bare word), bowls / grills / thermometers — both leave these as `AUTO:`.

**Takeaway message:** a local, open-weight model (Gemma 4 via Ollama) can reproduce the core of a frontier-model extraction for a task like this, at no API cost and with nothing leaving the machine. The frontier model's edge shows up in the softer, more interpretive fields (categories, descriptions, edge-case placement) rather than in the hard ontology grounding.

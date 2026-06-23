#!/usr/bin/env python3
"""Reconcile ungrounded (AUTO:) entities across one or more ontogpt OWL extractions.

When SPIRES grounding fails, ontogpt mints a placeholder IRI in the AUTO
namespace (``http://example.org/auto/<url-encoded label>``). Across several input
files the *same* real-world entity can surface under *different* AUTO IRIs just
because its label was written slightly differently ("Soy Lecithin" vs
"Soy lecithin", "Fudge Mint Cookie" vs "Fudge Mint Cookies"), or because it was
grounded in one file but not in another ("Cocoa" -> FOODON:03301072 in file A,
AUTO:Cocoa in file B). Each variant becomes its own class, so the merged
ontology fills up with near-duplicates.

This tool loads every extraction into ONE rdf graph, clusters labelled entities
by a normalised form of their label, and within each cluster picks a single
canonical IRI:

  * if the cluster contains a GROUNDED ontology term (an OBO-style IRI such as
    .../obo/FOODON_03301072), that term is canonical -- AUTO variants fold INTO
    the real term (we never rewrite a grounded term into an AUTO one);
  * otherwise the most representative AUTO IRI in the cluster is chosen and the
    other AUTO variants fold into it.

Two sub-commands:

  plan   load the inputs, compute the clusters, write a review-friendly mapping
         TSV (old_iri -> new_iri) and print the proposed merges. Nothing is
         changed -- you (or the user) can edit the TSV before applying.

  apply  load the inputs, MERGE them into one graph, rewrite every triple using
         the (possibly hand-edited) mapping so duplicates collapse onto their
         canonical IRI, keep a single canonical label per target, and write the
         merged + reconciled ontology.

Run with the interpreter that ships ontogpt/oaklib (it has rdflib), e.g.
    "$(dirname "$(command -v ontogpt)")/python" reconcile_auto.py plan ...
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from collections import defaultdict
from urllib.parse import unquote

try:
    from rdflib import Graph, Literal, URIRef
    from rdflib.namespace import RDFS, XSD
except ImportError:  # pragma: no cover
    sys.exit(
        "rdflib is required. Run this script with the venv python that ships "
        "ontogpt, e.g.:\n"
        '  "$(dirname "$(command -v ontogpt)")/python" '
        + sys.argv[0]
        + " ..."
    )

DEFAULT_AUTO_NS = "http://example.org/auto/"
# An IRI is treated as a "grounded" ontology term (a valid fold target) when its
# local part looks like PREFIX_NNN with an upper-case prefix (FOODON_03301072,
# UO_0000021, BFO_0000040, ...). This matches OBO PURLs and CURIE-expanded terms
# while excluding the schema's own structural / product classes.
DEFAULT_GROUND_RE = r"[/#:][A-Z]{2,}[A-Za-z0-9]*_[0-9]{2,}(?:$|[^A-Za-z0-9])"

_FMT_BY_EXT = {
    "ttl": "turtle",
    "turtle": "turtle",
    "n3": "n3",
    "nt": "nt",
    "jsonld": "json-ld",
    "json": "json-ld",
    "owl": "xml",
    "rdf": "xml",
    "xml": "xml",
}


def fmt_for(path: str) -> str:
    return _FMT_BY_EXT.get(path.lower().rsplit(".", 1)[-1], "xml")


def normalize(label: str, fold_plurals: bool = False) -> str:
    """Case / whitespace / punctuation-insensitive key for clustering labels.

    With ``fold_plurals`` a single trailing 's' is stripped from each word so
    regular plurals match their singular ("cookies"=="cookie", "oils"=="oil").
    This is a naive heuristic -- it does not handle irregular plurals
    ("tomatoes", "berries", "leaves") and can over-merge, so always review the
    mapping it produces.
    """
    s = unicodedata.normalize("NFKC", label).lower().strip()
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)  # punctuation -> space
    s = re.sub(r"\s+", " ", s).strip()
    if fold_plurals:
        s = " ".join(
            w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w
            for w in s.split(" ")
        )
    return s


def load_graph(inputs: list[str]) -> Graph:
    g = Graph()
    for path in inputs:
        g.parse(path, format=fmt_for(path))
    return g


def label_for(g: Graph, iri: str) -> str | None:
    for o in g.objects(URIRef(iri), RDFS.label):
        return str(o)
    # No explicit label: recover it from the AUTO local part (url-decoded).
    local = iri.rsplit("/", 1)[-1]
    return unquote(local) if local else None


def collect(g: Graph, auto_ns: str, ground_re):
    """Return (auto_labels, ground_labels): iri -> label string."""
    auto_labels: dict[str, str] = {}
    ground_labels: dict[str, str] = {}
    for s in set(g.subjects()):
        if not isinstance(s, URIRef):
            continue
        iri = str(s)
        if iri.startswith(auto_ns):
            lbl = label_for(g, iri)
            if lbl:
                auto_labels[iri] = lbl
        elif ground_re.search(iri):
            lbl = label_for(g, iri)
            if lbl:
                ground_labels[iri] = lbl
    return auto_labels, ground_labels


def _canonical_score(item):
    """Sort key for choosing the best AUTO label in an all-AUTO cluster.

    Prefer a Title-Case-looking label, then the shorter surface form (so the
    singular wins over the plural and a trailing-punctuation variant loses),
    then the smallest IRI for determinism."""
    iri, label = item
    title_like = 0 if label == label.title() else 1
    return (title_like, len(label), iri)


def build_clusters(auto_labels, ground_labels, fold_plurals):
    """Yield dicts describing each cluster that produces at least one remap."""
    auto_by_key = defaultdict(list)
    for iri, lbl in auto_labels.items():
        auto_by_key[normalize(lbl, fold_plurals)].append((iri, lbl))

    ground_by_key = defaultdict(list)
    for iri, lbl in ground_labels.items():
        ground_by_key[normalize(lbl, fold_plurals)].append((iri, lbl))

    clusters = []
    for key in sorted(auto_by_key):
        members = sorted(auto_by_key[key])
        grounded = sorted(ground_by_key.get(key, []))
        if grounded:
            canon_iri, canon_label = grounded[0]
            reason = "ground" if len(grounded) == 1 else "ground-CONFLICT"
        elif len(members) > 1:
            canon_iri, canon_label = min(members, key=_canonical_score)
            reason = "dedup"
        else:
            continue  # lone AUTO, no grounded twin -> nothing to merge
        remaps = [(iri, lbl) for iri, lbl in members if iri != canon_iri]
        if not remaps:
            continue
        clusters.append(
            {
                "key": key,
                "canon_iri": canon_iri,
                "canon_label": canon_label,
                "reason": reason,
                "remaps": remaps,
                "grounded_alts": grounded[1:],
            }
        )
    return clusters


def cmd_plan(args):
    g = load_graph(args.input)
    ground_re = re.compile(args.ground_regex)
    auto_labels, ground_labels = collect(g, args.auto_ns, ground_re)
    clusters = build_clusters(auto_labels, ground_labels, args.fold_plurals)

    rows = []
    for c in clusters:
        for old_iri, old_label in c["remaps"]:
            rows.append((old_iri, c["canon_iri"], old_label, c["canon_label"], c["reason"]))

    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write("# AUTO reconciliation map. Columns are tab-separated.\n")
        fh.write("# Edit or delete rows before `apply`; rows where old==new are ignored.\n")
        fh.write("# old_iri\tnew_iri\told_label\tnew_label\treason\n")
        for r in rows:
            fh.write("\t".join(r) + "\n")

    n_ground = sum(1 for c in clusters if c["reason"].startswith("ground"))
    n_dedup = sum(1 for c in clusters if c["reason"] == "dedup")
    conflicts = [c for c in clusters if c["reason"] == "ground-CONFLICT"]
    print(f"Loaded {len(args.input)} file(s): "
          f"{len(auto_labels)} AUTO entities, {len(ground_labels)} grounded terms.")
    print(f"Proposed merges: {len(rows)} entities collapse into {len(clusters)} canonical "
          f"IRIs  ({n_ground} fold AUTO->grounded, {n_dedup} fold AUTO->AUTO).")
    if not clusters:
        print("Nothing to reconcile -- no duplicate labels found across the inputs.")
    for c in clusters:
        arrow = "==>" if c["reason"].startswith("ground") else "-->"
        print(f"\n  [{c['reason']}] canonical: {c['canon_label']}  <{c['canon_iri']}>")
        for old_iri, old_label in c["remaps"]:
            print(f"      {arrow} {old_label!r}  <{old_iri}>")
    if conflicts:
        print(f"\nWARNING: {len(conflicts)} cluster(s) matched MORE THAN ONE grounded term "
              "(reason=ground-CONFLICT). The first was chosen; review these rows.")
    print(f"\nMapping written to {args.output}")
    print("Review it, then run `apply` to produce the reconciled ontology.")


def read_map(path: str):
    """Return (remap: old_iri->new_iri, labels: new_iri->new_label)."""
    remap: dict[str, str] = {}
    labels: dict[str, str] = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            old_iri, new_iri = parts[0].strip(), parts[1].strip()
            if not old_iri or not new_iri or old_iri == new_iri:
                continue
            remap[old_iri] = new_iri
            if len(parts) >= 4 and parts[3].strip():
                labels[new_iri] = parts[3].strip()
    return remap, labels


def cmd_apply(args):
    g = load_graph(args.input)
    remap, labels = read_map(args.map)
    if not remap:
        print("Mapping is empty -- writing the merged inputs unchanged.")

    ng = Graph()
    for prefix, ns in g.namespaces():
        ng.bind(prefix, ns)

    def sub(term):
        if isinstance(term, URIRef) and str(term) in remap:
            return URIRef(remap[str(term)])
        return term

    for s, p, o in g:
        ng.add((sub(s), p, sub(o)))

    # Each canonical target may now carry several rdfs:label values (its own plus
    # the folded-in ones). Collapse to a single canonical label.
    for new_iri, lbl in labels.items():
        t = URIRef(new_iri)
        ng.remove((t, RDFS.label, None))
        ng.add((t, RDFS.label, Literal(lbl, datatype=XSD.string)))

    out_fmt = args.format or fmt_for(args.output)
    ng.serialize(destination=args.output, format=out_fmt)

    targets = len(set(remap.values()))
    print(f"Merged {len(args.input)} file(s); folded {len(remap)} duplicate "
          f"entit{'y' if len(remap) == 1 else 'ies'} into {targets} canonical IRI(s).")
    print(f"Reconciled ontology written to {args.output} (format: {out_fmt}).")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--input", "-i", nargs="+", required=True,
                        help="one or more ontogpt OWL extractions")
    common.add_argument("--auto-ns", default=DEFAULT_AUTO_NS,
                        help=f"AUTO namespace prefix (default: {DEFAULT_AUTO_NS})")
    common.add_argument("--ground-regex", default=DEFAULT_GROUND_RE,
                        help="regex marking an IRI as a grounded fold target")
    common.add_argument("--fold-plurals", action="store_true",
                        help="also treat singular/plural label variants as equal "
                             "(more merges, slightly riskier)")

    p_plan = sub.add_parser("plan", parents=[common], help="compute & write the mapping")
    p_plan.add_argument("--output", "-o", required=True, help="mapping TSV to write")
    p_plan.set_defaults(func=cmd_plan)

    p_apply = sub.add_parser("apply", parents=[common], help="apply a mapping")
    p_apply.add_argument("--map", required=True, help="mapping TSV from `plan`")
    p_apply.add_argument("--output", "-o", required=True, help="reconciled ontology to write")
    p_apply.add_argument("--format", help="rdflib output format (default: from -o extension)")
    p_apply.set_defaults(func=cmd_apply)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

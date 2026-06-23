#!/usr/bin/env bash
#
# enrich_ontology.sh -- enrich a (reconciled) ontogpt ontology with the labels,
# definitions and is-a ancestors of the ontology terms it grounded to.
#
# It auto-detects which source ontologies the extraction grounded against
# (FOODON, UO, BFO, RO, CHEBI, ...) by scanning the IRIs, then for each one:
#   1. collects the grounded term CURIEs,
#   2. expands them to their is-a ancestors with OAK (runoak),
#   3. extracts that subset as OBO (carries labels + definitions + is_a in one shot),
# and finally merges every subset back into the input with ROBOT. This is the
# generalised, "written on the fly" form of the hand-coded enrichment snippet:
# it adapts to whatever ontologies actually appear in the data.
#
# Usage:
#   enrich_ontology.sh --input ONT.owl --out FINAL.owl [options]
#
# Required:
#   --input PATH      The ontology to enrich (e.g. reconciled.owl).
#   --out   PATH      Where to write the enriched ontology.
#
# Options:
#   --tmp DIR         Scratch dir for per-ontology subsets
#                     (default: <dir of --out>/tmp-enrich).
#   --adapters MAP    Override the prefix -> OAK adapter mapping, comma-separated,
#                     e.g. "BFO=sqlite:obo:ro,RO=sqlite:obo:ro". A prefix not in
#                     the map defaults to sqlite:obo:<lowercased-prefix>.
#   --only "P1 P2"    Restrict enrichment to these prefixes (space-separated).
#   -h, --help        Show this help.
#
# Requires: runoak (installed with ontogpt) and ROBOT (`brew install robot`)
# with a Java runtime. The first runoak call for a given ontology downloads its
# SQLite database, which can be large and slow; later runs use the cache.
set -euo pipefail

usage() { sed -n '2,/^set -euo/p' "$0" | sed 's/^# \{0,1\}//; $d'; }

INPUT="" OUT="" TMP="" ADAPTERS="" ONLY=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --input) INPUT="$2"; shift 2 ;;
    --out)   OUT="$2";   shift 2 ;;
    --tmp)   TMP="$2";   shift 2 ;;
    --adapters) ADAPTERS="$2"; shift 2 ;;
    --only)  ONLY="$2";  shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

[[ -n "$INPUT" && -f "$INPUT" ]] || { echo "ERROR: --input file required" >&2; exit 2; }
[[ -n "$OUT" ]] || { echo "ERROR: --out required" >&2; exit 2; }
command -v runoak >/dev/null || { echo "ERROR: runoak not on PATH (activate the venv)" >&2; exit 1; }
command -v robot  >/dev/null || { echo "ERROR: robot not found (brew install robot)" >&2; exit 1; }

[[ -n "$TMP" ]] || TMP="$(dirname "$OUT")/tmp-enrich"
mkdir -p "$TMP"

# Resolve the OAK adapter for a prefix (override map wins, else sqlite:obo:<lower>).
adapter_for() {
  local p="$1" lower kv
  lower="$(printf '%s' "$p" | tr '[:upper:]' '[:lower:]')"
  if [[ -n "$ADAPTERS" ]]; then
    IFS=',' read -ra _pairs <<< "$ADAPTERS"
    for kv in "${_pairs[@]}"; do
      [[ "${kv%%=*}" == "$p" ]] && { printf '%s' "${kv#*=}"; return; }
    done
  fi
  printf 'sqlite:obo:%s' "$lower"
}

# Detect grounded prefixes: local parts shaped PREFIX_NNN with an upper-case
# prefix. Excludes AUTO IRIs (example.org/auto/<label>) and gro: classes.
if [[ -n "$ONLY" ]]; then
  read -ra PREFIXES <<< "$ONLY"
else
  # (read loop rather than `mapfile`, which the default macOS bash 3.2 lacks)
  PREFIXES=()
  while IFS= read -r _line; do
    [[ -n "$_line" ]] && PREFIXES+=("$_line")
  done < <(
    { grep -oE "[/#:][A-Z]{2,}[A-Za-z0-9]*_[0-9]{2,}" "$INPUT" || true; } \
      | sed -E 's@^[/#:]([A-Z]{2,}[A-Za-z0-9]*)_[0-9]+@\1@' | sort -u
  )
fi

if [[ ${#PREFIXES[@]} -eq 0 ]]; then
  echo "No grounded ontology terms found in $INPUT -- nothing to enrich."
  echo "Copying input to $OUT."
  robot merge --input "$INPUT" --output "$OUT"
  exit 0
fi

echo "Grounded ontologies detected: ${PREFIXES[*]}"
merge_args=(--input "$INPUT")

for p in "${PREFIXES[@]}"; do
  adapter="$(adapter_for "$p")"
  ids="$TMP/${p}.ids"; anc="$TMP/${p}.anc"; obo="$TMP/${p}.enriched.obo"

  # 1. Grounded CURIEs for this prefix (PREFIX_NNN -> PREFIX:NNN).
  { grep -oE "${p}_[0-9]+" "$INPUT" || true; } | sort -u | sed 's/_/:/' > "$ids"
  if [[ ! -s "$ids" ]]; then
    echo "  $p: no ids, skipping"; continue
  fi
  echo "  $p: $(wc -l < "$ids" | tr -d ' ') seed term(s) via $adapter"

  # 2. Expand seeds to their is-a ancestors.
  { runoak -i "$adapter" ancestors -p i .idfile "$ids" --output-type csv 2>/dev/null || true; } \
    | awk -F'\t' 'NR>1 && $1 ~ /:/ {print $1}' | sort -u > "$anc"
  cat "$ids" >> "$anc"
  sort -u -o "$anc" "$anc"

  # 3. Extract the subset as OBO (labels + definitions + is_a parents).
  runoak -i "$adapter" extract .idfile "$anc" --dangling -p i -O obo -o "$obo"
  merge_args+=(--input "$obo")
done

# 4. Merge everything with ROBOT.
echo "Merging into $OUT ..."
robot merge "${merge_args[@]}" --output "$OUT"
echo "Enriched ontology written to $OUT"

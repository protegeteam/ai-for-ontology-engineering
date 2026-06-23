#!/usr/bin/env bash
#
# extract_parallel.sh -- run `ontogpt extract` over many input files concurrently.
#
# Each input file is extracted independently against one LinkML schema with one
# model, producing one output file per input. Extractions are run in parallel
# with GNU parallel; failures are isolated (one bad file does not stop the rest)
# and a per-file log is kept.
#
# Usage:
#   extract_parallel.sh --schema SCHEMA --model MODEL [options] FILE [FILE ...]
#
# Required:
#   --schema PATH     LinkML schema file, or a packaged template name
#                     (e.g. grocery-item.yaml, or recipe.Recipe).
#   --model  NAME     Model id passed to ontogpt -m
#                     (e.g. ollama/gemma4:26b, gpt-4o, claude-3-5-sonnet-latest).
#
# Options:
#   --out DIR         Output directory (default: ontogpt-out/extractions).
#   --jobs N          Concurrent extractions. Default: 4 for cloud models,
#                     2 for ollama/* (a single local server has limited
#                     concurrency and high RAM use -- raise only if your
#                     OLLAMA_NUM_PARALLEL and memory allow).
#   --format FMT      ontogpt -O output format (default: owl). The reconcile and
#                     enrich steps need owl; change only if you want raw yaml/json.
#   --no-quiet        Do not pass ontogpt --quiet=true (show all log output).
#   -h, --help        Show this help.
#
# Notes:
#   * Cloud models need the relevant API key exported (e.g. OPENAI_API_KEY).
#   * Local models need the Ollama server running (`ollama serve`) and the model
#     pulled (`ollama pull <model>`).
#   * Inputs must be text files; convert PDFs/HTML to text first.
set -euo pipefail

usage() { sed -n '2,/^set -euo/p' "$0" | sed 's/^# \{0,1\}//; $d'; }

SCHEMA="" MODEL="" OUTDIR="ontogpt-out/extractions" JOBS="" FORMAT="owl" QUIET=1
inputs=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --schema) SCHEMA="$2"; shift 2 ;;
    --model)  MODEL="$2";  shift 2 ;;
    --out)    OUTDIR="$2"; shift 2 ;;
    --jobs)   JOBS="$2";   shift 2 ;;
    --format) FORMAT="$2"; shift 2 ;;
    --no-quiet) QUIET=0;   shift ;;
    -h|--help) usage; exit 0 ;;
    --) shift; inputs+=("$@"); break ;;
    -*) echo "Unknown option: $1" >&2; usage; exit 2 ;;
    *)  inputs+=("$1"); shift ;;
  esac
done

[[ -n "$SCHEMA" ]] || { echo "ERROR: --schema is required" >&2; exit 2; }
[[ -n "$MODEL"  ]] || { echo "ERROR: --model is required"  >&2; exit 2; }
[[ ${#inputs[@]} -gt 0 ]] || { echo "ERROR: no input files given" >&2; exit 2; }
command -v ontogpt  >/dev/null || { echo "ERROR: ontogpt not on PATH (activate the venv)" >&2; exit 1; }
command -v parallel >/dev/null || { echo "ERROR: GNU parallel not found (brew install parallel)" >&2; exit 1; }

# Sensible default concurrency by model type.
if [[ -z "$JOBS" ]]; then
  case "$MODEL" in
    ollama/*|ollama_chat/*) JOBS=2 ;;
    *) JOBS=4 ;;
  esac
fi

mkdir -p "$OUTDIR" "$OUTDIR/logs"
JOBLOG="$OUTDIR/parallel.joblog"
: > "$JOBLOG"

global_opts=()
[[ "$QUIET" == 1 ]] && global_opts+=(--quiet=true)

echo "Extracting ${#inputs[@]} file(s) -> $OUTDIR  (model=$MODEL, jobs=$JOBS, format=$FORMAT)"

# --halt never: keep going if one file fails. --results: per-job stdout/stderr.
# {/.} = input basename without extension.
set +e
parallel --will-cite -j "$JOBS" --halt never --joblog "$JOBLOG" \
  --results "$OUTDIR/logs/{/.}" --tagstring '{/}' \
  ontogpt "${global_opts[@]}" extract \
    -i {} -t "$SCHEMA" -m "$MODEL" -O "$FORMAT" -o "$OUTDIR/{/.}.$FORMAT" \
  ::: "${inputs[@]}"
set -e

fails=$(awk 'NR>1 && $7 != 0 {c++} END {print c+0}' "$JOBLOG")
total=${#inputs[@]}
ok=$((total - fails))
echo "Done: $ok/$total succeeded -> $OUTDIR/*.$FORMAT"
if [[ "$fails" -gt 0 ]]; then
  echo "WARNING: $fails file(s) failed. Inspect logs:"
  echo "  joblog : $JOBLOG"
  echo "  stderr : $OUTDIR/logs/*/stderr"
  exit 1
fi

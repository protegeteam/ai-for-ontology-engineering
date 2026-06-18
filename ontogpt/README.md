# OntoGPT Demos

[OntoGPT](https://github.com/monarch-initiative/ontogpt) is a tool for extracting structured, ontology-grounded knowledge from text using large language models. This folder contains the demo files used in the short course.

```
ontogpt/
├── demo1/   Data extraction with a predefined Recipe schema
├── demo2/   The same extraction running on a local model
└── demo3/   Extraction with a custom schema
```

---

## 1. Prerequisites

### 1.1 Install Python 3.13.x

OntoGPT requires Python `>=3.10,<3.14`, so install **Python 3.13.x** if you don't already have it. Expand the instructions for your operating system:

<details>
<summary><b>macOS</b></summary>

```bash
# With Homebrew (https://brew.sh)
brew install python@3.13

# Verify
python3.13 --version
```

Alternatively, download the official installer from <https://www.python.org/downloads/release/python-3137/>.

</details>

<details>
<summary><b>Windows</b></summary>

```powershell
# With winget (Windows Package Manager)
winget install Python.Python.3.13

# Verify
py -3.13 --version
```

Alternatively, download the installer from <https://www.python.org/downloads/windows/> and tick **"Add python.exe to PATH"** during setup.

</details>

<details>
<summary><b>Linux (Ubuntu/Debian)</b></summary>

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.13 python3.13-venv

# Verify
python3.13 --version
```

On other distributions use your package manager, or [pyenv](https://github.com/pyenv/pyenv) (`pyenv install 3.13.7`) to get a 3.13.x interpreter.

</details>

### 1.2 Create a virtual environment and install OntoGPT

Create the virtual environment with **Python 3.13** and install OntoGPT from GitHub with `pip`:

```bash
# Create and activate a Python 3.13 virtual environment
python3.13 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Upgrade pip, then install OntoGPT (our fork with the patches below)
pip install --upgrade pip
pip install "git+https://github.com/johardi/ontogpt.git@fix/spires-null-like-recursion"
```

> **Note — why a fork?** We maintain a fork of OntoGPT that includes patches not yet merged upstream (the `fix/spires-null-like-recursion` branch fixes a recursion issue in the SPIRES grounding code). To use the original, unpatched OntoGPT instead, run:
>
> ```bash
> pip install ontogpt
> ```

Verify the installation:

```bash
ontogpt --version
```

OntoGPT installs the [OAK](https://github.com/INCATools/ontology-access-kit) toolkit, so the `runoak` command is also available inside the virtual environment.

### 1.3 Set the OpenAI API key

Demo 1 uses an OpenAI model by default, so export your API key:

**macOS / Linux**

```bash
export OPENAI_API_KEY="sk-..."
```

**Windows (PowerShell)**

```powershell
$env:OPENAI_API_KEY = "sk-..."
```
---

## Demo 1 — Recipe extraction with a predefined schema

Using the predefined `recipe` schema that ships with OntoGPT to build an ontology about a *Spinach and Feta Turkey Burger* recipe.

Run from inside the `demo1/` folder:

```bash
cd demo1
```

### Extract

```bash
ontogpt --quiet=true extract \
  -i allrecipes-spinach-feta-turkey-burgers.txt \
  -t recipe.Recipe \
  -O yaml \
  -o spinach-feta-turkey-burgers.yaml
```

**Parameters**

| Flag | Meaning |
| ---- | ------- |
| `-i` | Path to the input text file to extract from. |
| `-t` | The schema/template to extract against (required). `recipe` is the predefined template and `.Recipe` selects the root class within it. |
| `-O` | Output serialization format. One of: `json`, `yaml`, `pickle`, `md`, `html`, `owl`, `turtle`, `jsonl`, `kgx`, `csv`, `tsv`. |
| `-o` | Where to write the result. Without `-o`, output goes to stdout (the terminal). |

`--quiet=true` is a global option (it goes *before* the `extract` subcommand) that suppresses the warning/log messages OntoGPT prints to the terminal, keeping the output clean.

The extracted recipe — grounded to ontology terms such as `FOODON:` (food ontology) and `UO:` (units of measurement) — is written to `spinach-feta-turkey-burgers.yaml`.

<details>
<summary><b>Enriching the output ontology (Optional)</b></summary>

<br>

The enrichment step adds the labels, definitions, and `is_a` ancestors of the grounded terms to an OWL ontology. It needs an OWL export of the extraction, so first produce one:

```bash
ontogpt --quiet=true extract \
  -i allrecipes-spinach-feta-turkey-burgers.txt \
  -t recipe.Recipe \
  -O owl \
  -o spinach-feta-turkey-burgers.owl
```

> **Requires:** `runoak` (installed with OntoGPT) and [ROBOT](http://robot.obolibrary.org/) with a Java runtime. On macOS: `brew install robot`.

```bash
mkdir -p tmp

# 1. Collect the grounded ontology IDs, converting the full OBO IRIs to CURIEs.
grep -oE "(FOODON|UO|BFO|RO)_[0-9]+" \
  spinach-feta-turkey-burgers.owl | sort -u | sed 's/_/:/' \
  > tmp/grounded-ids.txt

# 2. Split by source ontology.
grep -E "^FOODON:"   tmp/grounded-ids.txt > tmp/foodon-ids.txt
grep -E "^UO:"       tmp/grounded-ids.txt > tmp/uo-ids.txt
grep -E "^(BFO|RO):" tmp/grounded-ids.txt > tmp/ro-ids.txt

# 3. For each ontology: expand seeds to their is-a ancestors, then extract a
# subset as OBO (carries labels + definitions + is_a parents in one shot).
for prefix in foodon uo ro; do
  runoak -i sqlite:obo:$prefix ancestors -p i .idfile \
    tmp/${prefix}-ids.txt --output-type csv 2>/dev/null \
    | awk -F'\t' 'NR>1 && $1 ~ /:/{print $1}' | sort -u \
    > tmp/${prefix}-anc.txt
  cat tmp/${prefix}-ids.txt >> tmp/${prefix}-anc.txt
  sort -u -o tmp/${prefix}-anc.txt tmp/${prefix}-anc.txt
  runoak -i sqlite:obo:$prefix extract .idfile \
    tmp/${prefix}-anc.txt --dangling -p i \
    -O obo -o tmp/${prefix}-enriched.obo
done

# 4. Ontology merge using ROBOT tool.
robot merge \
  --input spinach-feta-turkey-burgers.owl \
  --input tmp/foodon-enriched.obo \
  --input tmp/uo-enriched.obo \
  --input tmp/ro-enriched.obo \
  --output spinach-feta-turkey-burgers.enriched.owl
```

The first `runoak` call against a given ontology downloads its SQLite database (this can be large and slow on first run); subsequent runs use the cached copy.

</details>

---

## Demo 2 — Run the extraction on a local model with Ollama

This demo runs the **same** extraction as Demo 1, but against a model served locally by [Ollama](https://ollama.com) instead of OpenAI — no API key required and nothing leaves your machine.

### 2.1 Install Ollama

Expand the instructions for your operating system:

<details>
<summary><b>macOS</b></summary>

```bash
brew install ollama
# or download the app from https://ollama.com/download
```

Then start the server (the desktop app does this automatically):

```bash
ollama serve
```

</details>

<details>
<summary><b>Windows</b></summary>

Download and run the installer from <https://ollama.com/download/windows>. Ollama runs as a background service after installation.

</details>

<details>
<summary><b>Linux</b></summary>

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

</details>

### 2.2 Pull the model

```bash
ollama pull gemma4:26b
```

> **Note:** The model tag must exactly match a model available in the [Ollama library](https://ollama.com/library). Pick a tag that fits your machine's memory — large models need substantial RAM/VRAM.

List the models you have available locally:

```bash
ollama list
```

### 2.3 Extract

Add the `-m ollama/<model>` flag to point OntoGPT at the local model. Run from inside the `demo2/` folder:

```bash
cd demo2

ontogpt --quiet=true extract \
  -i allrecipes-spinach-feta-turkey-burgers.txt \
  -t recipe.Recipe \
  -m ollama/gemma4:26b \
  -O yaml \
  -o spinach-feta-turkey-burgers.yaml
```

---

## Demo 3 — Extraction with a custom schema

Demos 1 and 2 used the predefined `recipe` template that ships with OntoGPT. This demo shows how to write **your own schema** and extract against it — the exercise from our short course where we build a small **grocery ontology** from a product label.

The input is the ingredient panel of a box of *Back to Nature Fudge Mint Cookies*, and the goal is to turn it into ontology classes: the product, the food it is, and the (possibly nested) ingredients that food is made of. We reuse the local `ollama/gemma4:26b` model from Demo 2, so no API key is required.

### 3.1 The custom schema

A schema is a [LinkML](https://linkml.io) YAML file that tells OntoGPT *what* to pull out of the text and *how* to ground it. Our schema, [`grocery-item.yaml`](./demo3/grocery-item.yaml), defines three classes:

| Class | Role |
| ----- | ---- |
| `GroceryItem` | The packaged product (the `tree_root`, i.e. the top-level thing being extracted). Carries a label, a description, the food it *contains*, and its ingredient statements. |
| `FoodStuff` | Any food substance — the whole product, a compound ingredient, or a simple ingredient. Annotated with `annotators: sqlite:obo:foodon`, so each one is grounded against the [Food Ontology (FOODON)](https://foodon.org). |
| `IngredientStatement` | A single "*parent* contains *ingredient*" fact. This is what lets the schema capture **multi-level nesting** — e.g. the cookie contains a fudge coating, and the fudge coating in turn contains cocoa and soy lecithin. |

The schema also embeds an `owl.template` (a Jinja snippet on `GroceryItem`) that emits the OWL axioms directly — `SubClassOf` and `ObjectSomeValuesFrom( gro:hasIngredient ... )` restrictions — so the extraction can be written straight out as an ontology.

### 3.2 Extract

Run from inside the `demo3/` folder:

```bash
cd demo3

ontogpt extract \
  -i grocery-fudge-mint-cookies.txt \
  -t grocery-item.yaml \
  -m ollama/gemma4:26b \
  -O owl \
  -o grocery-fudge-mint-cookies.owl
```

**Parameters**

| Flag | Meaning |
| ---- | ------- |
| `-i` | Path to the input text file — here the cookie's label and ingredient list. |
| `-t` | The schema/template. **This is the key difference from Demos 1 & 2:** instead of a packaged template name (`recipe.Recipe`), we pass a **path to our own LinkML schema file**. The root class (`GroceryItem`) is the one marked `tree_root: true`, so no `.ClassName` suffix is needed. |
| `-m` | The model to use — the local `gemma4:26b` served by Ollama, the same one pulled in Demo 2. |
| `-O` | Output format. We use `owl` because the goal is to build an ontology. |
| `-o` | Where to write the result. |

### 3.3 The result

The extraction is written to [`grocery-fudge-mint-cookies.owl`](./demo3/grocery-fudge-mint-cookies.owl). Open the file in [Protégé](https://protege.stanford.edu) to browse the resulting class hierarchy.

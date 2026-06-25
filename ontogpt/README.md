# OntoGPT Demos

[OntoGPT](https://github.com/monarch-initiative/ontogpt) is a tool for extracting structured, ontology-grounded knowledge from text using large language models. This folder contains the demo files used in the short course.

```
ontogpt/
├── demo1/   Data extraction with a predefined Recipe schema
├── demo2/   The same extraction running on a local model
├── demo3/   Extraction with a custom schema
└── demo4/   Batch extraction over many files, orchestrated by a Claude Code skill
```

---

## 1. Prerequisites

### 1.1 Install Python 3.13.x

OntoGPT requires Python `>=3.10,<3.14`, so install **Python 3.13.x** if you don't already have it. Expand the instructions for your operating system:

**macOS**

```bash
# With Homebrew (https://brew.sh)
brew install python@3.13

# Verify
python3.13 --version
```

Alternatively, download the official installer from [https://www.python.org/downloads/release/python-3137/](https://www.python.org/downloads/release/python-3137/).



**Windows**

```powershell
# With winget (Windows Package Manager)
winget install Python.Python.3.13

# Verify
py -3.13 --version
```

Alternatively, download the installer from [https://www.python.org/downloads/windows/](https://www.python.org/downloads/windows/) and tick **"Add python.exe to PATH"** during setup.



**Linux (Ubuntu/Debian)**

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.13 python3.13-venv

# Verify
python3.13 --version
```

On other distributions use your package manager, or [pyenv](https://github.com/pyenv/pyenv) (`pyenv install 3.13.7`) to get a 3.13.x interpreter.



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
  -O owl \
  -o spinach-feta-turkey-burgers.owl
```

**Parameters**


| Flag | Meaning                                                                                                                                |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `-i` | Path to the input text file to extract from.                                                                                           |
| `-t` | The schema/template to extract against (required). `recipe` is the predefined template and `.Recipe` selects the root class within it. |
| `-O` | Output serialization format. One of: `json`, `yaml`, `pickle`, `md`, `html`, `owl`, `turtle`, `jsonl`, `kgx`, `csv`, `tsv`.            |
| `-o` | Where to write the result. Without `-o`, output goes to stdout (the terminal).                                                         |


`--quiet=true` is a global option (it goes *before* the `extract` subcommand) that suppresses the warning/log messages OntoGPT prints to the terminal, keeping the output clean.

The extracted recipe — grounded to ontology terms such as `FOODON:` (food ontology) and `UO:` (units of measurement) — is written to `spinach-feta-turkey-burgers.owl`.

### Other predefined schemas

`recipe` is just one of the many schemas that ship with OntoGPT. You run any of them the same way — swap the `-t` value for one of the names below and point `-i` at a relevant text. The full list lives in the [templates folder](https://github.com/monarch-initiative/ontogpt/tree/main/src/ontogpt/templates); here are ten examples:

| `-t` value | What it extracts |
| --- | --- |
| [`recipe.Recipe`](https://github.com/monarch-initiative/ontogpt/blob/main/src/ontogpt/templates/recipe.yaml) | Food recipes — ingredients and preparation steps (used above). |
| [`drug.DrugMechanismSet`](https://github.com/monarch-initiative/ontogpt/blob/main/src/ontogpt/templates/drug.yaml) | Drug mechanisms of action and the diseases they treat. |
| [`mendelian_disease.MendelianDisease`](https://github.com/monarch-initiative/ontogpt/blob/main/src/ontogpt/templates/mendelian_disease.yaml) | Mendelian (genetic) diseases — genes, symptoms, and inheritance. |
| [`gocam.GoCamAnnotations`](https://github.com/monarch-initiative/ontogpt/blob/main/src/ontogpt/templates/gocam.yaml) | Gene Ontology Causal Activity Models — molecular activities and pathways. |
| [`phenotype.Trait`](https://github.com/monarch-initiative/ontogpt/blob/main/src/ontogpt/templates/phenotype.yaml) | Computational phenotypes described as entity–quality traits. |
| [`biotic_interaction.Container`](https://github.com/monarch-initiative/ontogpt/blob/main/src/ontogpt/templates/biotic_interaction.yaml) | Ecological interactions between species (predator/prey, host/parasite). |
| [`environmental_metadata.Dataset`](https://github.com/monarch-initiative/ontogpt/blob/main/src/ontogpt/templates/environmental_metadata.yaml) | Metadata describing environmental datasets and samples. |
| [`reaction.Reaction`](https://github.com/monarch-initiative/ontogpt/blob/main/src/ontogpt/templates/reaction.yaml) | Biochemical reactions — their participants and the pathways they belong to. |
| [`maxo.MaxoAnnotations`](https://github.com/monarch-initiative/ontogpt/blob/main/src/ontogpt/templates/maxo.yaml) | Medical actions — treatments and procedures used to manage a disease. |
| [`personinfo.Container`](https://github.com/monarch-initiative/ontogpt/blob/main/src/ontogpt/templates/personinfo.yaml) | A general, non-biomedical example — people, their occupations, and relationships. |

The `-t` value is always `<schema>.<RootClass>`, where `<schema>` is the predefined template (without `.yaml`) and `<RootClass>` is its top-level class.

**Enriching the output ontology (Optional)**

On its own, the extraction only records the grounded term *IDs* (e.g. `FOODON:00001287`) — not their labels, definitions, or place in the class hierarchy. The simplest way to pull all of that in is to let the ontology **import** the reference ontologies it grounds against, so a tool like [Protégé](https://protege.stanford.edu) can resolve every term online.

Open `spinach-feta-turkey-burgers.owl` in [Protégé](https://protege.stanford.edu) and add an import for each reference ontology through the GUI:

1. Go to the **Active ontology** tab.
2. In the **Ontology imports** tab, find **Direct Imports** and click the **+** (add) button.
3. In the import wizard, choose **Import an ontology contained in a document located on the web** and enter the ontology URL:
   - `http://purl.obolibrary.org/obo/foodon.owl`
   - `http://purl.obolibrary.org/obo/ro.owl`
4. Click **Continue → Finish**, then repeat for the second URL.

Together these cover every grounded term in the extraction: `foodon.owl` resolves the `FOODON:`, `UO:`, and `BFO:` terms (FOODON already imports those), and `ro.owl` resolves the `RO:` relations. Protégé fetches the imported ontologies and resolves every grounded term to its label, definition, and `is_a` ancestors.

---

## Demo 2 — Run the extraction on a local model with Ollama

This demo runs the **same** extraction as Demo 1, but against a model served locally by [Ollama](https://ollama.com) instead of OpenAI — no API key required and nothing leaves your machine.

### 2.1 Install Ollama

Expand the instructions for your operating system:

**macOS**

```bash
brew install ollama
# or download the app from https://ollama.com/download
```

Then start the server (the desktop app does this automatically):

```bash
ollama serve
```



**Windows**

Download and run the installer from [https://ollama.com/download/windows](https://ollama.com/download/windows). Ollama runs as a background service after installation.



**Linux**

```bash
curl -fsSL https://ollama.com/install.sh | sh
```



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
  -O owl \
  -o spinach-feta-turkey-burgers.owl
```

---

## Demo 3 — Extraction with a custom schema

Demos 1 and 2 used the predefined `recipe` template that ships with OntoGPT. This demo shows how to write **your own schema** and extract against it — the exercise from our short course where we build a small **grocery ontology** from a product label.

The input is the ingredient panel of a box of *Back to Nature Fudge Mint Cookies*, and the goal is to turn it into ontology classes: the product, the food it is, and the (possibly nested) ingredients that food is made of. We reuse the local `ollama/gemma4:26b` model from Demo 2, so no API key is required.

### 3.1 The custom schema

A schema is a [LinkML](https://linkml.io) YAML file that tells OntoGPT *what* to pull out of the text and *how* to ground it. Our schema, `[grocery-item.yaml](./demo3/grocery-item.yaml)`, defines three classes:


| Class                 | Role                                                                                                                                                                                                                     |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `GroceryItem`         | The packaged product (the `tree_root`, i.e. the top-level thing being extracted). Carries a label, a description, the food it *contains*, and its ingredient statements.                                                 |
| `FoodStuff`           | Any food substance — the whole product, a compound ingredient, or a simple ingredient. Annotated with `annotators: sqlite:obo:foodon`, so each one is grounded against the [Food Ontology (FOODON)](https://foodon.org). |
| `IngredientStatement` | A single "*parent* contains *ingredient*" fact. This is what lets the schema capture **multi-level nesting** — e.g. the cookie contains a fudge coating, and the fudge coating in turn contains cocoa and soy lecithin.  |


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


| Flag | Meaning                                                                                                                                                                                                                                                                                 |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `-i` | Path to the input text file — here the cookie's label and ingredient list.                                                                                                                                                                                                              |
| `-t` | The schema/template. **This is the key difference from Demos 1 & 2:** instead of a packaged template name (`recipe.Recipe`), we pass a **path to our own LinkML schema file**. The root class (`GroceryItem`) is the one marked `tree_root: true`, so no `.ClassName` suffix is needed. |
| `-m` | The model to use — the local `gemma4:26b` served by Ollama, the same one pulled in Demo 2.                                                                                                                                                                                              |
| `-O` | Output format. We use `owl` because the goal is to build an ontology.                                                                                                                                                                                                                   |
| `-o` | Where to write the result.                                                                                                                                                                                                                                                              |


### 3.3 The result

The extraction is written to `[grocery-fudge-mint-cookies.owl](./demo3/grocery-fudge-mint-cookies.owl)`. Open the file in [Protégé](https://protege.stanford.edu) to browse the resulting class hierarchy.

---

## Demo 4 — Batch extraction over many files with a Claude Code skill

Demo 3 turned **one** product label into an ontology. Demo 4 scales that to a collection of text documments and merges the results into a **single, de-duplicated, enriched ontology** — the `[demo4/](./demo4)` folder holds several cookie/biscuit products, all extracted against the same `[grocery-item.yaml](./demo4/grocery-item.yaml)` schema from Demo 3.

Doing this by hand means running `ontogpt extract` once per file and then cleaning up the seams between files, because the same ingredient often comes out differently in each one. The work is packaged as a reusable **[Claude Code](https://docs.claude.com/en/docs/claude-code) skill** named `ontogpt-extract` that orchestrates three stages for you:

> **Is this Claude-only?** Two different "models" are in play, and only one of them is Claude:
>
> - **The driver** is Claude Code — a *skill* is a Claude Code (and skills.sh-compatible) feature: an instruction file plus scripts that the agent reads and runs. So you orchestrate Demo 4 *with* Claude Code.
> - **The extractor** is whatever LLM you point OntoGPT at. The skill simply passes your choice to `ontogpt extract -m <model>`. Demo 4 reuses the **local** `ollama/gemma4:26b` from Demo 2 — no API key, nothing leaves your machine — but `gpt-4o`, `claude-`*, or any other supported model works just as well.
>
> Nothing here is tied to a Claude *model*. The three scripts under `[demo4/skills/ontogpt-extract/scripts/](./demo4/skills/ontogpt-extract/scripts)` are plain Bash + Python and can be run by hand with no agent at all.

### 4.1 Prerequisites

In addition to the [Section 1](#1-prerequisites) setup (Python venv + OntoGPT, which also provides `runoak`):


| Tool                                                       | Why                                      | Install (macOS)                            |
| ---------------------------------------------------------- | ---------------------------------------- | ------------------------------------------ |
| [Claude Code](https://docs.claude.com/en/docs/claude-code) | Runs the skill                           | `npm install -g @anthropic-ai/claude-code` |
| [Node.js](https://nodejs.org) (`npx`)                      | Installs the skill via skills.sh         | `brew install node`                        |
| GNU `parallel`                                             | Stage 1 fan-out                          | `brew install parallel`                    |
| [ROBOT](http://robot.obolibrary.org/) + Java               | Stage 3 ontology merge                   | `brew install robot`                       |
| Ollama + `gemma4:26b`                                      | The local extraction model (from Demo 2) | see [Section 2.1–2.2](#21-install-ollama)  |


### 4.2 Install the skill with skills.sh

The skill is bundled in this repo under `[demo4/skills/ontogpt-extract](./demo4/skills/ontogpt-extract)`. Install it with the [skills.sh](https://www.skills.sh) CLI (`npx skills`, no global install needed). Run from inside the `demo4/` folder:

```bash
cd demo4

# Install from the bundled copy into this project's .claude/skills/
npx skills add https://github.com/protegeteam/ai-for-ontology-engineering --skill ontogpt-extract

# Pull the latest version of every installed skill later on
npx skills update
```

### 4.3 Run it

Launch Claude Code in the `demo4/` folder and give it the goal in plain language:

```text
Process all the text files and produce an ontology that represents the knowledge in the text
```

Claude recognises the task, invokes the `ontogpt-extract` skill, and asks **which model** to use (pick `gemma4:26b`). It then runs the processing steps. The outputs land under `demo4/ontogpt-out/`, including the the enriched final ontology `final.owl` that you can open in Protégé

For the seven products, the extraction grounds ~36 distinct FOODON terms; reconciliation folds the spelling variants; and enrichment expands those terms to ~148 with their `is_a` ancestors, labels and definitions — yielding a `final.owl` whose seven products each link through `gro:containsFoodStuff` / `gro:hasIngredient` to their (possibly nested) ingredients.

> **Note (macOS):** the bundled `enrich_ontology.sh` uses a `read` loop rather than the bash-4 `mapfile` builtin, so it works with the default `/bin/bash` 3.2 that ships on macOS. ROBOT also needs a Java runtime on your `PATH`.


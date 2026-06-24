# Editing Ontology with OWL-MCP

This guide shows how to edit the [`grocery.owl`](./grocery.owl) ontology in natural language by connecting an AI assistant to the **[owl-mcp](https://github.com/ai4curation/owl-mcp)** server.

`owl-mcp` is a [Model Context Protocol](https://modelcontextprotocol.io) server that lets an LLM read and modify OWL ontologies on disk. It keeps the ontology in memory, syncs it back to the file, and exposes tools such as `add_axiom`, `add_axioms`, `remove_axiom`, `find_axioms`, `get_labels_for_iri`, and `ontology_metadata`. Axioms are expressed in **OWL functional syntax**.

Two setups are documented below:

1. **[Claude Cowork](#1-claude-cowork)** — a hosted assistant; register owl-mcp in the developer config.
2. **[A local model with LM Studio](#2-local-model-with-lm-studio)** — fully offline using the `Gemma4-26B-A4B-QAT` model.

> Throughout this guide, replace that path with the location of `grocery.owl` on your own machine.

---

## Prerequisites

`owl-mcp` is launched with **`npx`**, which ships with [Node.js](https://nodejs.org/). Install it once:

```bash
# Option A — Homebrew (macOS)
brew install node

# Option B — download the installer from https://nodejs.org/
```

Confirm it is available and note the **absolute path** — you will need it for LM Studio later.

```bash
which npx
# e.g. /opt/homebrew/opt/node@22/bin/npx
```

`npx -y owl-mcp serve` downloads and runs the latest server on first use, so there is nothing else to install.

---

## 1. Claude Cowork

### 1.1 Add owl-mcp to the developer config

owl-mcp is a **local** MCP server so we will need to register it through the developer config:

1. Open **Claude Cowork** and go to **Settings → Developer**.
2. Click **Edit Config**. This opens the MCP configuration JSON in your editor.
3. Add `owl-mcp` under `mcpServers` (merge it in if the file already lists other servers):

   ```json
   {
     "mcpServers": {
       "owl-mcp": {
         "command": "uvx",
         "args": ["owl-mcp"]
       }
     }
   }
   ```

4. **Save** the file and **restart Claude Cowork**. After it reloads you should see the owl-mcp tools
   (`add_axiom`, `find_axioms`, …) become available.

### 1.2 Grant folder access and edit with prompts

Give Cowork access to the folder that contains `grocery.owl` (the workspace/project folder). Once the folder is shared, you can point at the file with an **`@` mention** (e.g. `@grocery.owl`) and Cowork resolves it from the shared folder.

**Tell it which file to work on:**

> Use the owl-mcp tools to work on the ontology @grocery.owl. First show me the current parent classes of `CocoaButter` and `Semolina`.

**Example 1 — reparent two classes:**

> In @grocery.owl, make `CocoaButter` a subclass of `FoodStuff` instead of its current parent, and make `Semolina` a subclass of `WheatFlour` instead of `FoodStuff`. Remove the old `SubClassOf` axioms so each class has only the new parent.

**Example 2 — add a label and a description:**

> Add the label "Cocoa Butter" to `CocoaButter` using `rdfs:label`, and add a description using `rdfs:comment`.

Cowork will call the owl-mcp tools and the changes are written straight back to `grocery.owl`. Open the grocery ontology file using Protege to see the immediate changes.

---

## 2. Local model with LM Studio

This setup runs everything locally — no data leaves your machine.

### 2.1 Install LM Studio

1. Download LM Studio for your platform from **<https://lmstudio.ai>**.
2. macOS: open the `.dmg` and drag **LM Studio** into **Applications**. Launch it.
3. MCP support requires a recent build (LM Studio **0.4.x** or newer). Update from **Settings** if needed.

### 2.2 Download and load the model

1. Click the **Model Search** icon (the magnifying-glass icon).
2. Search for **`google/gemma-4-26b-a4b-qat`** and download it. (QAT = quantization-aware-trained; it gives good quality at a smaller memory footprint.)
3. Switch to the **Chat** tab and **load** the Gemma 4 model from the model selector at the buttom.

### 2.3 Add owl-mcp through the server (MCP) settings

1. In the **Chat** tab, open the **Integrations** selector using the hammer icon at the bottom.
2. Click the **+** button and select **Edit mcp.json**.
3. Add the `owl-mcp` server:

   ```json
   {
     "mcpServers": {
       "owl-mcp": {
         "command": "npx",
         "args": [ "owl-mcp" ]
       }
     }
   }
   ```

4. **Save** `mcp.json`. LM Studio will start the server and list its tools.

### 2.4 Enable the integration

In the chat, open the **Integrations** selector again and make sure **`owl-mcp` is selected** for the conversation. The model can only call the owl-mcp tools when this integration is active.

### 2.5 Edit the ontology with prompts

Local models like Gemma are less able to infer the working file than Cowork, so **include the absolute path to `grocery.owl` in every prompt** that modifies it.

**Example 1 — reparent two classes:**

> Using the owl-mcp tools on the file `/absolute/path/to/grocery.owl`: make `CocoaButter` a subclass of `FoodStuff` instead of `ButterProduct`, and make `Semolina` a subclass of `WheatFlour` instead of `FoodStuff`. Remove the old `SubClassOf` axioms.

**Example 2 — add a label and a description:**

> Using the owl-mcp tools on the file `/absolute/path/to/grocery.owl`: add `rdfs:label` "Cocoa Butter" to `CocoaButter`, and add an `rdfs:comment` description.

If the model returns an answer without calling a tool, remind it explicitly: *"Call the owl-mcp tools to perform the actions."*

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| owl-mcp tools never appear | Verify `npx -y owl-mcp serve` runs in a terminal; in LM Studio use the **absolute** path to `npx` in `mcp.json`. |
| Model answers but never edits the file | Make sure the integration/connector is **enabled**, and pass the **absolute** path to `grocery.owl` in the prompt. |
| "File not found" | Double-check the absolute path; owl-mcp operates on the file path exactly as given. |
| Changes don't show in Protégé | Reload the file — owl-mcp writes to disk, but an already-open editor may hold a stale copy. |

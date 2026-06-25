# AI for Ontology Engineering

Supporting materials and reference resources for the Protégé Short Course on ontology tools powered by AI.

This repository collects hands-on examples that show how AI can help with everyday ontology work — turning plain text into ontology classes, and editing an existing ontology by simply describing the change you want. Each tool lives in its own folder with a step-by-step guide.

## Tools

### [OntoGPT](./ontogpt) — from text to ontology

[OntoGPT](https://github.com/monarch-initiative/ontogpt) uses a large language model to pull structured, ontology-grounded knowledge out of text, guided by a predefined schema. You point it at a document (a recipe, a product label, a paper) and it extracts the relevant entities and grounds them to terms in existing ontologies.

The demos walk from a single extraction with a built-in schema, to running fully offline on a local model, to writing your own schema, and finally to batch-processing many files at once.

### [OWL-MCP](./owl-mcp) — edit ontologies in natural language

[owl-mcp](https://github.com/ai4curation/owl-mcp) connects an AI assistant directly to an OWL ontology on disk. Instead of clicking through an editor, you describe the change in plain language — "make `CocoaButter` a subclass of `FoodStuff`" — and the assistant makes the edit and saves it back to the file.

The guide covers two setups: a hosted assistant (Claude Cowork) and a fully local model (LM Studio).

## Getting started

Pick the tool you want to try and follow the README in its folder — each one lists its own prerequisites and walks through the examples.

## License

See [LICENSE](./LICENSE).

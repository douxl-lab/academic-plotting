# Academic Plotting

Standalone, source-faithful adaptation of [Orchestra Research's academic-plotting skill](https://github.com/Orchestra-Research/AI-Research-SKILLs/tree/main/20-ml-paper-writing/academic-plotting). The original Git repository was cloned and its skill history extracted locally; original author, source commits and MIT attribution are documented. This GitHub repository starts as a content archive and does not claim the original commits as its remote ancestors.

It creates publication-ready figures from research sources:
- Real-data line/grouped bar/horizontal bar/scatter/heatmap/box/violin plots with explicit statistical semantics and unit conversion
- Editable-text SVG and vector PDF, fully decoded 300-DPI PNG, a self-contained reproduction script, source/spec/style and numerical/provenance checks
- Evidence-bound architecture/mechanism prompts and exact canonical RFS/PaperBanana v1 request/result interchange
- Honest separation of numerical, integrity, visual, scientific and native-editability checks

The statistical renderer is an academic-plotting extension. It is not a renamed copy of RFS's minimal three-chart helper. Model rendering and native PPTX reconstruction use separately installed, authorized backends; this package itself performs neither paid generation nor generated-code execution.

## Install and discover

Python 3.11+:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

Install this repository directory as an academic-plotting skill in your host's skill search path. SKILL.md is the entrypoint; agents/openai.yaml supplies optional UI metadata. Automatic discovery remains enabled. Prompt example:

> Use $academic-plotting to turn these original experimental measurements into a paper-ready figure. Confirm the unit of replication and error-bar definition, preserve all observations, and deliver SVG/PDF/PNG plus reproducible code and a numerical audit.

## Genuine-data quickstart

The optional example uses actual public Iris plant observations from the installed scikit-learn package, not simulated experimental scores. It identifies the corrected source variant and records original byte identity.

```sh
python -m pip install -r requirements-test.txt
python scripts/prepare_iris_example.py --output /tmp/iris-input --chart bar
python scripts/numeric_plot.py --data /tmp/iris-input/measurements.csv --spec /tmp/iris-input/plot-spec.json --style assets/style.json --output /tmp/iris-figure --original /tmp/iris-input/iris-sklearn-original.csv --derivation-code /tmp/iris-input/prepare_code.py
python scripts/verify_numeric.py /tmp/iris-figure
cd /tmp/iris-figure
python plot_code.py --data source.csv --spec plot-spec.json --style style.json --output reproduced --original original-source.csv --derivation-code derivation_code.py
```

Use --chart hbar, heatmap, box, violin or scatter with fresh input/output directories. The example has categorical measurement dimensions, so it deliberately does not invent a training curve. See [numeric specification](references/numeric-specification.md). Output directories are never overwritten.

## Paired RFS/PaperBanana workflows

```sh
python scripts/exchange.py check-peer --paperbanana-root /path/to/PaperBanana
python scripts/exchange.py prepare-request --spec ORIGINAL_FIGURE_SPEC.json --output /tmp/new-request
python /path/to/PaperBanana/skill/exchange.py validate-request --request /tmp/new-request/request.json
python scripts/exchange.py inspect --bundle SELECTED_BUNDLE --spec ORIGINAL_FIGURE_SPEC.json --expected-kind diagram
python scripts/exchange.py consume --bundle SELECTED_BUNDLE --spec ORIGINAL_FIGURE_SPEC.json --expected-kind diagram --output /tmp/accepted-reference
```

These are offline, read-only peer operations. There is no provider call, credential lookup or automatic code execution. Generation requires separate, specific authorization for disclosed sources and costs. Integrity acceptance leaves scientific/visual review pending; an image bundle is not an editable native diagram. See [exchange details](references/exchange.md) and [scientific diagram prompts](references/diagram-generation.md).

## Tests and verification limits

```sh
python -m pip install -r requirements-test.txt
python -m pytest -q
python scripts/check_release.py
PAPERBANANA_ROOT=/path/to/PaperBanana RFS_SKILL_ROOT=/path/to/research-figure-skill/research-figure python -m pytest tests/test_exchange.py -q
```

The optional peer test uses the actual PaperBanana CLI, its unchanged exporter and the RFS CLI. No model is invoked. Tests also use genuine Iris observations, exact per-row source-lineage checks, real Matplotlib artists and SVG/PDF/PNG outputs, independent statistics, reproduction and adversarial failures (including valid-CRC PNG payloads that cannot decompress). [Testing notes](docs/TESTING.md) describe what was and was not established.

## Upstream history and licensing

The original skill was authored by AmberLJC and appeared in upstream commit 6710bc7360123bf7947374f58483879d630ace5b. It was genuinely cloned from upstream and extracted locally with Git's subdirectory history filter. The local filtered base 74c96ac6bc1c5d45b9b54bd2e0b3b1427f3a698c preserves that original author/date/message and contains this skill only. Source snapshot: 773a52944ba4747a18bd4ae9ade53fff041adcbc.

The current GitHub repository starts from its own initialization commit, followed by this attributed content archive. It does not import the original or locally filtered Git ancestors. Source URLs, commit identifiers, authorship and licenses provide provenance here; a separate local filtered-history bundle supports private traceability without publishing unrelated monorepo history.

Original/adapted skill and local additions: [MIT](LICENSE). The separately vendored canonical protocol remains [Apache-2.0](protocol/LICENSE-APACHE-2.0). See [third-party notices](THIRD_PARTY_NOTICES.md) for exact commits and dataset rights. No model weights, private user data or authentication material belong in a publication.

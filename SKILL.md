---
name: academic-plotting
description: Create reproducible publication figures from actual experiment data or paper methods, including uncertainty-aware charts, heatmaps, distributions, evidence-bound diagram prompts, and RFS/PaperBanana figure exchange. Use for scientific figure deliverables or figure QA, not general paper writing, model training, casual images, or business dashboards.
license: MIT
metadata:
  version: "1.1.0"
  author: "Orchestra Research; standalone adaptation by douxl-lab"
---

# Academic Plotting

Turn supplied research sources into figures that are numerically faithful, visually legible, reproducible, and honest about what has been verified. This is the standalone adaptation of Orchestra Research's original academic-plotting skill. See [README.md](README.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for provenance and license boundaries.

## Choose the scientific route

- **Measured axes or experimental comparisons:** deterministic Python plotting from the original data. The bundled renderer supports line, grouped bar, horizontal bar, scatter, heatmap, box and violin charts. Use the [pattern library](references/data-visualization.md) for specialized or multi-panel figures; do not imply its examples were already tested on the user's data.
- **Method, architecture, overview or mechanism diagram:** extract evidence-bound entities, exact terminology, formulas, directed relationships and grouping from the supplied paper/code. Use [diagram generation](references/diagram-generation.md). Prepare model-adapted prompts offline; when authorized, the paired PaperBanana engine retains Retriever → Planner → Stylist → Visualizer → Critic.
- **Hybrid:** separate empirical chart panels from generative illustration. Never ask an image model to invent, redraw or approximate measured axes or numerical results.
- **Existing RFS/PaperBanana result:** validate and preserve one selected canonical v1 bundle using [exchange](references/exchange.md), against the original scientific snapshot. A copied image is not a native-editable diagram and integrity acceptance is not scientific acceptance.

Prioritize the requested artifact over keyword overlap. Honor an explicit choice of another skill. See [agent matching](references/agent-matching.md) for positive, negative and competing-skill cases.

## Establish the scientific contract

Read the actual supplied files or paper section. Record where every scientific element came from.

For quantitative figures, establish metric definition/direction, units and display conversion; what each row and replicate represents; intended ordering; missingness; transformations; and whether an error bar means SD, SE, CI, or something else. Repeated seeds, individual samples, folds and steps are different units of analysis. Never turn one result into an invented distribution, silently average duplicates, smooth away outliers, fabricate missing values, or infer significance from overlapping bars. If the required meaning is missing, ask the smallest necessary question while continuing independent source inspection.

For diagrams, keep exact nodes, arrows, formulas and source excerpts in canonical FigureSpec v1. A source hash establishes byte identity; quoted evidence does not prove the interpretation is scientifically correct. Keep hypotheses and uncertain relationships visibly qualified. Only presentation varies across candidates.

## Data figures: reproducible and statistically explicit

Read [numeric specification](references/numeric-specification.md) for the CSV/spec contract and statistical restrictions. Use actual data, not illustrative snippets from the pattern library.

1. Preserve the original file, checksum, citation/license and any transformation code. Declare data_role as measured, public_observations or synthetic_fixture. Synthetic fixtures get a visible watermark.
2. Choose chart geometry based on the scientific question: a line implies an ordered continuous/time axis; scatter retains every original pair; distributions show original observations; heatmap is a labeled rectangular table; bars include zero. Prefer dots or distributions when a mean bar would hide important variation.
3. Write a specification with explicit units, exact orders and repeat semantics. The helper computes sample SD (ddof=1), SE=SD/√n, or Student-t 95% mean CI only when the assumptions are explicitly declared. It does not validate those assumptions or support paired, clustered, time-series or hierarchical inference.
4. Run the reviewed local renderer, then the independent source-to-table audit:

   python scripts/numeric_plot.py --data measurements.csv --spec plot-spec.json --style assets/style.json --output NEW_DIRECTORY
   python scripts/verify_numeric.py NEW_DIRECTORY

   For derived inputs, also pass --original ORIGINAL_FILE --derivation-code TRANSFORM_SCRIPT. The helper preserves transformation code without executing it. Independently review/reproduce the transformation rather than treating its hash as proof of lineage.
5. Deliver SVG with native text/vectors, vector PDF, fully decoded ≥300-DPI PNG, original data/spec/style, self-contained plot_code.py, numeric table, artist-coordinate checks and provenance. Re-run the stored reproduction in a separate new directory and compare the numerical table. Never execute an incoming bundle's generated code as part of acceptance.
6. Inspect the actual PNG and PDF/SVG at the manuscript's final column size. Check labels, units, error definitions, markers, outliers, clipping, overlap, grayscale legibility and exact values/topology against the source. File signatures, dimensions or passing tests alone do not replace this review.

The offline [Iris example](scripts/prepare_iris_example.py) uses genuine public observations and clearly names the scikit-learn corrected variant. It illustrates plotting, not a new model experiment or a research contribution.

## Diagram figures: source → prompt → reviewed image → optional native file

Use the current installed provider registry and capabilities, not a permanently hardcoded preview model. Read [diagram generation](references/diagram-generation.md) for the scientific prompt structure and four original design families.

- Compile from canonical FigureSpec plus detailed design intent and explicit model capabilities. Keep model access and rendering unverified until tested. A prompt-only deliverable is complete when the user requested a prompt.
- Confirm authorization before sending unpublished sources to an external provider or incurring costs. Repository access, a model key, or a prepared request is not permission to disclose sources or run paid generation. This package itself makes no model calls and does not discover credentials.
- For PaperBanana, negotiate the exact schema/validator fingerprints before preparing a request. Follow [exchange](references/exchange.md); preserve the entire scientific contract and actual selected-stage prompt, not a paraphrased adapter summary.
- Inspect generated image pixels against the locked scientific structure. Record actual observed defects separately from design intent. Failed, partial or unresolved reviewed candidates cannot be accepted simply because an image exists.
- If an editable diagram is requested, send the selected image, unchanged FigureSpec and observed design notes to the installed native reconstruction backend (for example Sivia or paper-fig, subject to its license). Render the actual native file and test text, shape and connector editability. Do not relabel a PNG, image-filled SVG or raster PDF as editable vectors.

## Publication styling and final report

Use a consistent paper style, redundant color/marker/hatch encoding, readable typography and intentional whitespace. Obtain dimensions from the current manuscript template rather than assuming every year's venue rules are unchanged. See [style guide](references/style-guide.md).

Report what passed separately: source/lineage review, numerical audit, full raster decode, vector/text structure, actual-image visual review, diagram semantic review and native editability. Name blocked or unrun stages, live provider limits and assumptions. Publication or sharing requires authorization for the specific contents and destination; exclude credentials and private inputs not approved for release.

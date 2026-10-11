# Validation and remaining limits

## Reproduce the checks

Install requirements-test.txt and run python -m pytest -q. Genuine-data tests require the optional scikit-learn example dependency. Without it they skip explicitly; do not call that a genuine-data pass.

For actual cross-repository checks, set PAPERBANANA_ROOT to a trusted installed PaperBanana checkout and RFS_SKILL_ROOT to its paired research-figure skill directory, then run the full suite. The peer tests execute those projects' known CLI/export code in temporary output directories. They never execute Python supplied by a result bundle, call providers or mutate the peer source trees.

Compatibility was exercised on Python 3.12 against RFS 642389edbde500446def6014fe438f32e1d5a4b1 and PaperBanana c3269855ce3d5f2d3efe4434f91adb9fd1948245. The workflow matrix defines future CI on Python 3.11/3.12/3.13; defining it is not evidence those CI jobs have run.

## Scientific/data coverage

- Genuine Iris original bytes and installed corrected variant; 150 plants and four dimensions, reshaped to 600 original measured values or 150 retained scatter pairs
- Each derived row independently compared with original bundled source CSV, species and plant identity
- Bar/hbar SD, heatmap cell means, box medians/quartiles/whiskers/outliers, violin descriptive KDE/median, and sparse duplicate-x scatter points
- Independently recomputed mean, sample SD, SE, Student-t CI, inclusive quartiles and 1.5-IQR whiskers; fraction/percent and cm/mm conversion
- Missing/extra columns, nonfinite data, duplicate identity, omitted/reordered data, unsupported dimensions, dependence assumptions and single-observation fake error bars rejected
- Actual Matplotlib artists checked before export; vector/text SVG, parseable PDF with selectable text, complete PNG pixel decompression, and self-contained code reproduction

## Exchange coverage

- Exact actual PaperBanana CLI descriptor and request validation
- Actual unchanged PaperBanana export → academic-plotting inspect/consume → actual RFS CLI audit
- Original caller snapshot and source/table/scientific fingerprints preserved
- Byte-identical copied producer manifest, image, prompt, design, specification and inert code; separate consumer receipt and unchanged producer flags
- Chronological review sequences accept discarded earlier failure followed by explicit final success; reject a later final failure/pending, accepted=false, contradictory outcome or unresolved last record
- Corrupt bytes, stale schema/validator, source/science tampering, duplicates, path traversal, case aliases, Windows reserved paths, symlinks and overwrite attempts rejected
- Valid-CRC PNG with invalid compressed IDAT: demonstrates why Image.verify() alone is insufficient and validates reopen/load() behavior

## Packaging and behavior coverage

scripts/check_release.py checks metadata, relative links, pinned protocol hashes, retained MIT notice, unintended private task markers and common credential patterns. It is a heuristic hygiene check, not a guarantee that every possible secret is detected. Independently inspect the exact staged/publication tree.

Bilingual matching cases distinguish numerical figures, method prompts, audits, exchange, insufficient input and competing explicit skills. Their structural tests are not a host automatic selection benchmark. Offline prompt compilation verifies immutable scientific text and provider capability adaptation; rendering/access remains unverified.

## Not established by this test suite

Live paid provider generation, account/model availability, actual host automatic skill selection, scientific correctness or authenticity of arbitrary supplied data, real i.i.d. assumptions, causal/significance claims, general paired/clustered/hierarchical inference, transformation semantics beyond the known Iris example, native editable PPTX/draw.io reconstruction, and comprehensive future compatibility are not claimed as passed.

Actual figure visual inspection at final manuscript size is required in addition to programmatic checks. Passing hashes or an artist ledger cannot prove that an externally altered figure matches its data. Prompt preparation and bundle acceptance remain distinct from finished scientific/native-file acceptance.

## Local validation result (2026-10-11)

The initial frozen candidate passed 89 tests with zero skips on Python 3.12.14, with both actual peer paths enabled. Dependencies observed: Matplotlib 3.10.8, NumPy 2.3.5, SciPy 1.17.0, Pillow 12.3.0, pypdf 6.10.0, jsonschema 4.26.0, scikit-learn 1.8.0 and pytest 9.1.1. The skill creator frontmatter validator and candidate hygiene checks passed.

Six genuine-data plots were generated and independently audited, with complete 1650×1020 PNG decompression at approximately 300 DPI, vector/text SVG/PDF structure and exact original-row lineage. The self-contained bar plot reproduction produced an identical numerical table. Actual PNG inspection caught and corrected categorical label loss caused by reapplying a linear Matplotlib scale after fixed ticks; the final bar/box/violin labels were re-inspected. Heatmap colorbar automatic rasterization was also caught by real vector tests and disabled.

Actual PNG review found no clipped labels or legend/data obstruction in this example. This is review of the example images at their configured 5.5-inch width, not certification of every future figure or final manuscript layout. PDF structure was parsed programmatically; independent reviewer checks and remote CI/publication verification remain separate stages.

An independent forward trial recreated genuine Iris scatter and bar figures, checked all 150 original scatter pairs and all 12 n=50 bar summaries against the original source using independent statistics, and inspected decoded/vector artifacts. It found an overly broad rejection of a repaired bundle's historical failed review. The consumer now checks the last explicit outcome against the overall status while preserving history, without inventing mandatory stage/source/round constraints absent from the canonical schema. Repaired-history acceptance, final-failure/accepted=false/contradictory/unresolved negative cases, and the actual producer's ordinary model-review history are covered. The revised frozen candidate passed 99 tests with zero skips, actual peers enabled.

# Canonical RFS / PaperBanana exchange

Verified against RFS commit 642389edbde500446def6014fe438f32e1d5a4b1 and PaperBanana commit c3269855ce3d5f2d3efe4434f91adb9fd1948245 on 2026-10-11. These are compatibility snapshots, not a promise that future main branches are compatible.

The exact Apache-2.0 protocol lives in protocol/contract.py, interop.py, prompt_compiler.py and the two JSON schemas. It is mirrored unchanged from the paired projects. Academic-plotting's stricter portable-path/review/full-image-decode rules live in scripts/exchange.py, so peer negotiation still compares the original schema and validator fingerprints. Do not copy the obsolete rfs_contract/artifacts adapter or accept legacy FigureSpec 0.1 as canonical v1.

## Offline preparation

Check the installed peer with the interpreter that has its exchange dependencies:

python scripts/exchange.py describe
python scripts/exchange.py check-peer --paperbanana-root /path/to/PaperBanana

Exact protocol name, version, figure schema, manifest schema, validator and request-format fingerprints must match. Failure means stop and update the paired installation; do not relax the check.

Build a canonical diagram specification from actual method/code sources. Preserve sources verbatim with checksums, evidence quotes and exact node/edge/group/label/formula constraints. Do not populate it with made-up research modules. Original data tables remain exact tables; statistical transformations need a separate explicit scientific specification.

python scripts/exchange.py prepare-request --spec ORIGINAL_FIGURE_SPEC.json --output NEW_REQUEST_DIRECTORY --candidates 2

This creates request.json, figure-spec.json and source.txt without invoking a model. It refuses plots and unsplit hybrid datasets. The paired PaperBanana CLI can validate offline:

python /path/to/PaperBanana/skill/exchange.py validate-request --request /path/to/NEW_REQUEST_DIRECTORY/request.json

Paid provider execution is outside this helper. Only after specific disclosure/cost authorization use the paired engine's documented run route with --allow-external. A timeout does not establish that the provider did not charge. Keep the selected model/provider explicit and do not silently switch credentials or destinations.

For a model-adapted draft without rendering:

python scripts/exchange.py compile-prompt --spec ORIGINAL_FIGURE_SPEC.json --design DESIGN_INTENT.md --capabilities CAPABILITIES.json --output NEW_DRAFT_DIRECTORY

Capabilities explicitly include provider, model and booleans supports_system_prompt, supports_reference_image, supports_editing; optional prompt_notes are actual provider guidance. Missing capabilities fail. A model label in a registry does not prove account access or editing support. Output is PROMPT_READY_NOT_RENDERED, with exact prompt, optional system prompt, metadata, unchanged FigureSpec and design intent.

## Inspect and consume one selected bundle

python scripts/exchange.py inspect --bundle SELECTED_BUNDLE --spec ORIGINAL_FIGURE_SPEC.json --expected-kind diagram
python scripts/exchange.py consume --bundle SELECTED_BUNDLE --spec ORIGINAL_FIGURE_SPEC.json --expected-kind diagram --output NEW_CONSUMER_DIRECTORY

Both commands require the caller's original scientific snapshot. Checks cover strict JSON, current schema, successful terminal status, producer verification flags, absence of errors and a consistent final selected review; discarded historical failed attempts may remain, portable nonlinked paths, declared byte counts/hashes, exact source/data tables, scientific fingerprints, actual prompt hash, image MIME and complete pixel decoding. PNG verify() alone is insufficient because a valid-CRC corrupt IDAT stream can evade it; every image is reopened and load() decompresses pixels.

The original producer manifest, actual image, prompt, design intent, FigureSpec and inert generated code are copied byte-for-byte to a new directory. No code from the bundle is imported or executed. The producer is never modified. A separate consumer-receipt.json records INTEGRITY_ACCEPTED_REVIEW_PENDING; producer flags stay unchanged. Hashes and source quotes do not imply scientific or native-editability certification.

Keep the three reconstruction inputs separate:
1. Original FigureSpec: scientific authority
2. Selected, actually inspected image: visual reference
3. Observed design notes: native object/layout/connector inventory and defects

The selected-stage design.md is generative intent, not observed-image evidence. Review the actual native output if Sivia/paper-fig reconstructs it. A request envelope, accepted bundle or reconstruction handoff is not a finished editable file.

## Actual compatibility evidence

The tests use the actual installed PaperBanana CLI to describe and validate requests, its actual unchanged exporter to make an offline result bundle, academic-plotting to consume it, and the actual RFS CLI to audit that same bundle. Those synthetic small-image mechanics fixtures prove interchange boundaries, not provider image quality. Genuine Iris tests separately exercise the real renderer, source lineage and vector/raster artifacts. Live paid generation and host automatic skill-selection are not claimed as tested.

## Review history and selected-attempt consistency

Review arrays preserve chronological attempts; the paired runtime appends rounds. A historical failure is not a failure of the repaired final image. When explicit outcome fields are present, require the final record to be successful and consistent with the overall status, without an explicit accepted=false or contradictory outcome. A historical pass followed by final failure/pending, contradictory final outcome fields, or a last record without a resolved outcome is rejected. Do not search the history for any convenient pass.

Arbitrary review stage/source/round fields are retained as metadata, not promoted to mandatory scientific or pixel-binding constraints absent from the canonical schema. The actual producer's source can name the pre-repair description, and rounds have no schema-level uniqueness guarantee. This adapter does not claim to independently establish which pixels a model saw.
The actual protocol's model_visual_review history normally has suggestions and no explicit passed/failed outcome. Overall completed/skipped/not_requested remains integrity evidence; it does not become scientific or observed-image approval. All history bytes are preserved and consumer scientific/visual review remains PENDING.

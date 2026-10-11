# Numeric specification and scientific meaning

The bundled helper is deliberately narrower than general Matplotlib. It rejects ambiguity rather than silently computing a scientifically different figure. Other reviewed plots may use normal Python/R plotting with equivalent provenance and QA.

## Input contract

CSV columns, in this exact order: series,x,replicate,value. Every row has an original measurement and a nonempty observation identity. Duplicate (series,x,replicate) identities, nonfinite/missing values, unexpected columns, unknown labels or omitted declared cells fail. Input code is never executed. Scatter permits sparse series/x combinations and retains duplicate x coordinates as separate original pairs.

The plot JSON uses schema_version "1.0.0" (an academic-plotting schema, distinct from RFS FigureSpec):

- chart: line, bar, hbar, scatter, heatmap, box or violin
- source: sha256 of the exact plotted CSV; title, uri, license, citation, data_role (measured/public_observations/synthetic_fixture)
- source optional: original_sha256, original_filename, derivation, dataset_variant. A declared original hash requires actual original bytes. Changed bytes require both a transformation description and --derivation-code. The mathematical verifier does not execute or certify transformation logic
- x: label, unit, display_unit, scale (linear/log)
- metric: name, kind (accuracy/length/time/generic), unit, display_unit, direction (higher/lower/descriptive), scale; optional valid_min/valid_max in original units
- series_order and x_order: unique strings, exact source coverage. Line x labels are numeric, strictly increasing and in the declared order. Categorical charts require unit=display_unit=1 and linear axes
- repeats: basis (independent_runs/observations/single), unit (what one replicate is), uncertainty (none/sd/se/ci95), assume_iid boolean, limitations text

Do not call steps on one trajectory independent runs, flatten folds from the same dataset into independent samples, or pool paired measurements to obtain an unpaired CI. Unsupported analysis should be performed separately with justified statistical methods. assume_iid is an explicit user/scientist assumption, not a machine-verified fact. Confidence coverage also needs suitable distribution/mean assumptions, especially for small n.

## Conversions and ranges

Supported linear conversions: fraction (1) ↔ percent (%); mm/cm/m; ms/s. Identical units, including documented custom metrics, remain unchanged. Other conversions fail. Accuracy ranges are [0,1] or [0,100] according to input units; explicit bounds cannot relax that range. Unknown and dimensionally incompatible conversions fail. Log axes require positive original coordinates and lower uncertainty endpoints; the helper never clips an invalid interval to make it fit.

## What each geometry means

- line/bar/hbar: an arithmetic mean at each declared series/x cell. n, sample SD and SE are recorded; error artists use the explicitly chosen uncertainty. Bars include the zero baseline, including all-negative data
- heatmap: an arithmetic mean in every complete series/x cell; no error bars. It is not automatically a confusion matrix or normalized probability table. Cells and the colorbar remain native vectors in SVG/PDF
- scatter: every source row is a separate (x,value) pair with its replicate identity. No averaging, sorting beyond declared x_order, imputation or artificial uncertainty
- box: original observations; median and linear/inclusive quartiles; whiskers reach the last observed value within 1.5 IQR; all outside observations are shown. No hidden filtering or inferential CI
- violin: original observations; descriptive Gaussian KDE with Scott bandwidth and 100 evaluation positions plus observed extrema/median. Requires at least two nonconstant values. Smoothing is descriptive geometry, not evidence of a learned distribution or inferential precision

Distribution and heatmap/scatter charts require uncertainty=none. A single-observation cell cannot receive SD/SE/CI. SE and ci95 require explicit assume_iid=true; SD can describe observed variability without asserting population independence.

## Outputs and honest verification

Every export writes source.csv, plot-spec.json, style.json, plot_code.py, figure.svg/pdf/png, numeric-table.json, numeric-acceptance.json, artifact-acceptance.json and provenance.json. Original-source/derivation bytes are included when declared. A pre-existing output is protected; failed exports remove only the newly reserved output directory.

Numeric acceptance checks actual Matplotlib line/scatter/bar/errorbar/mesh/distribution artists. The independent verifier recalculates mean/sample SD/SE/quartiles/whiskers from CSV using the standard library, with SciPy only for the Student-t quantile. It checks hashes and full PNG decoding, SVG native text/path structure and absence of raster wrappers, and a parseable one-page PDF with selectable text and no raster image objects.

These checks do not authenticate arbitrary research data, prove scientific truth or independence, or establish that an externally altered image still agrees with a forged artist ledger. Independently inspect the actual figure, source and caption. Keep integrity, numerical, visual and scientific acceptance distinct.

# Attribution and license boundaries

## Original academic-plotting skill: MIT

Original project: [Orchestra-Research/AI-Research-SKILLs](https://github.com/Orchestra-Research/AI-Research-SKILLs/tree/main/20-ml-paper-writing/academic-plotting).

The original SKILL.md and three references were introduced by AmberLJC in upstream commit [6710bc7360123bf7947374f58483879d630ace5b](https://github.com/Orchestra-Research/AI-Research-SKILLs/commit/6710bc7360123bf7947374f58483879d630ace5b). Source snapshot for this adaptation: 773a52944ba4747a18bd4ae9ade53fff041adcbc. The standalone filtered base is 74c96ac6bc1c5d45b9b54bd2e0b3b1427f3a698c; author, timestamp and commit message are preserved, while unrelated monorepo files are not part of the standalone branch tree/history.

The original MIT notice is retained verbatim in LICENSE: Copyright (c) 2025 Claude AI Research Skills Contributors. The skill instructions/references are adapted and local plotting, auditing, interoperability wrappers, tests and documentation have been added by douxl-lab. This repository does not imply upstream endorsement.

## Vendored exchange protocol: Apache-2.0

protocol/contract.py, interop.py, prompt_compiler.py, __init__.py and both JSON schemas are copied unchanged from [douxl-lab/research-figure-skill](https://github.com/douxl-lab/research-figure-skill) commit 642389edbde500446def6014fe438f32e1d5a4b1. contract.py, interop.py, prompt_compiler.py and both schemas are byte-identical to [douxl-lab/PaperBanana](https://github.com/douxl-lab/PaperBanana) commit c3269855ce3d5f2d3efe4434f91adb9fd1948245. PaperBanana is based on [dwzhu-pku/PaperBanana](https://github.com/dwzhu-pku/PaperBanana) / PaperVizAgent. The component remains Apache License 2.0, not MIT; its full license is retained as protocol/LICENSE-APACHE-2.0. Local stricter checks are in scripts/exchange.py and do not modify the vendored files.

This package does not bundle model SDKs, model weights, keys, credentials, private manuscripts, Sivia code, paper-fig helper code or third-party fonts. Those separately installed backends retain their own licenses. In particular Sivia's current non-commercial license must be respected; access does not imply commercial redistribution rights.

## Genuine public data example

The optional Iris example reads the dataset bundled with the installed scikit-learn distribution; no dataset file is vendored in this repository. It names the installed version and the corrected scikit-learn variant. Dataset attribution: Fisher, R. (1936). Iris [Dataset]. UCI Machine Learning Repository. [DOI 10.24432/C56C76](https://doi.org/10.24432/C56C76). UCI states [CC BY 4.0](https://archive.ics.uci.edu/dataset/53/iris). The helper preserves original bytes, reshapes measurements to long CSV or retains paired scatter measurements, records cm→mm display conversion, and exports attribution with its outputs. [scikit-learn documentation](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_iris.html) describes the historical corrected observations. Scikit-learn's code retains its own BSD license.

Synthetic unit fixtures are labeled test-only and are not research evidence. Public generated examples remain subject to applicable dataset/font/template/provider rights. Recheck licenses before redistribution or commercial use.

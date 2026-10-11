# Agent matching and research prompt behavior

Match scientific figure deliverables: experiment/result plots, paper architecture/method/mechanism figures, diagram prompt preparation, figure styling at manuscript size, or source/numeric/visual figure QA. Do not activate solely because a request says paper, chart or model. Respect an explicitly selected alternative skill.

The skill supports quantitative scientific work beyond the RFS minimal bar/line/scatter renderer. Use RFS/PaperBanana for canonical method-figure orchestration when available; use the statistical specification here for aggregation, uncertainty, distributions and real-data lineage. Do not silently convert one contract to the other or drop sources/rows to satisfy a simpler adapter.

Research prompt roles:
- Reader/extractor grounds exact scientific claims in the provided manuscript, code or data
- Statistical analyst chooses a justified unit of analysis and estimator, documenting missing assumptions
- Figure designer changes composition/style without changing science
- Artifact auditor checks actual files/pixels/objects and numerical consistency independently of appearance

With PaperBanana, preserve its actual five-agent architecture and source-locked protocol instead of inventing extra runtime agents. Capability fields adapt system prompts and reference-edit behavior; they do not certify that an account can access a model.

The bilingual corpus in tests/agent_matching_cases.json contains explicit expectations, including competing-skill cases and prompts with missing scientific inputs. Tests check corpus structure only. It is not a measured host auto-selection precision/recall benchmark. A realistic independent task trial can establish behavior for that trial; broad triggering claims require actual host invocation tests.

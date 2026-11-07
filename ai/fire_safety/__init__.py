"""Fire-safety analytics over NASA microgravity combustion data (Flame in Freefall).

Pure Python + numpy at runtime, so the API image needs nothing new:

* ``flex``       canonical FLEX (PSI-69) features and outcome labels, from table rows or ingested conditions
* ``model``      the FLEX outcome model: JSON artefact, numpy inference, applicability-domain checks
* ``scenarios``  mission cabin atmospheres, each cited to a corpus passage
* ``investigations``  per-investigation condition envelopes, scenario relevance ranking and insights

Training (scikit-learn) lives in ``train_flex_outcome.py`` and is never imported by the API.
"""

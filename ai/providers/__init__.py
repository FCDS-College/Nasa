"""Provider-neutral AI contracts and adapters (Phase 2 M1 / Sub-phase 2H, Task 2).

Layering: ``contracts`` is stdlib only and imports nothing else from this tree. ``cloud`` and
``local`` adapters implement the contracts; vendor SDKs (fastembed, sentence-transformers, cv2)
are imported lazily inside functions. Application code (``apps/api``) depends on the contracts
and on ``ai.routing``, never on a concrete adapter, except in its one wiring module
(``flame_api/ai_runtime.py``).
"""

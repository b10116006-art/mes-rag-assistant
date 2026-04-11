# CLAUDE.md — Development Rules

## 1. Minimal diff first

Before touching any file, state which files will be affected and why.
Prefer the smallest change that achieves the goal. Avoid refactoring adjacent code that was not part of the task.

## 2. Do not over-refactor

Do not rename variables, restructure modules, or clean up code unless it directly blocks the task.
Do not add type annotations, docstrings, or comments to code you did not change.

## 3. Protect app.py unless necessary

`app.py` is the working prototype. Do not restructure it during documentation or roadmap tasks.
When a feature phase requires changes to `app.py`, confirm the scope with the user first.

## 4. Do not expand into AOI or MES runtime scope

This repo handles RAG retrieval, LLM reasoning, memory retrieval, structured output, evaluation, and provider routing.

Do not add:
- AOI / computer vision code
- MES MQTT ingestion
- MES dashboard routes
- Machine utilization business logic

If a task requires those, it belongs in a different repo.

## 5. Explain impacted files before code changes

For any non-trivial change, list the files to be modified and the reason before writing code.

## 6. Prefer safe incremental development

Implement one phase at a time. Do not implement Phase 2 features while working on Phase 1.
Mark phases complete in `CHANGELOG.md` when acceptance criteria are met.

## 7. Update docs when roadmap or scope changes

If a phase is added, removed, or redefined, update `AI_ROADMAP.md` and `ARCHITECTURE.md`.
Do not let docs drift from the actual state of the code.

## 8. Follow additive-only principle for integration

When integrating with MES or AOI in the future:
- Add new functions / endpoints; do not modify existing working chains
- Do not change `MESAnalysisOutput` schema fields without versioning
- Do not break the existing Gradio demo path

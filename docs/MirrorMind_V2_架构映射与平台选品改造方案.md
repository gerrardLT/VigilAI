# MirrorMind V2 架构映射与平台选品改造方案

## 1. What Was Adopted From MirrorMind V2

The useful part of MirrorMind V2 for VigilAI is not the original business scenario. It is the architectural pattern:

- one unified agent entry instead of many isolated AI entry points
- process assets such as sessions, turns, and artifacts instead of only final outputs
- domain tools behind a shared orchestration layer
- structured workbench pages as companions, not the only primary workflow

VigilAI now maps that pattern into a practical, additive implementation.

## 2. Current Mapping In VigilAI

### MirrorMind concept: unified agent entry

Current VigilAI mapping:

- `/agent` shared workspace
- `AgentSession` with `domain_type`
- `ConversationEngine` for all domains
- `ToolRouter` for domain-aware capability dispatch

### MirrorMind concept: process assets

Current VigilAI mapping:

- `agent_sessions`
- `agent_turns`
- `agent_artifacts`
- `agent_jobs_v2`

These objects let the system persist intermediate reasoning outputs without replacing the legacy business tables.

### MirrorMind concept: platform layer above business domains

Current VigilAI mapping:

- shared platform in `app/backend/agent_platform/`
- opportunity domain in `app/backend/opportunity_domain/`
- product-selection domain in `app/backend/product_selection/`

This is the key architectural separation that prevents new commerce logic from leaking into the legacy `Activity` model.

## 3. Why Product Selection Must Stay Isolated

`product_selection` should not be merged into:

- `Activity`
- `Source`
- `Digest`

Reasons:

- the core objects are different
- the scoring logic is different
- the tracking workflow is different
- the platform adapters are different

If product selection were forced into `Activity`, the opportunity schema would become polluted with marketplace-specific semantics.

The current implementation avoids that by giving product selection its own repository, tables, API surface, frontend pages, and agent tools.

## 4. Implemented Product-Selection Design

### Shared pieces reused from the platform

- session creation
- turn persistence
- artifact persistence
- tool routing
- conversation response formatting

### Product-selection-specific pieces

- `selection_queries`
- `selection_opportunities`
- `selection_opportunity_signals`
- `selection_tracking_items`
- `ProductSelectionService`
- `SelectionQueryTool`
- `SelectionCompareTool`
- `/selection/*` pages

## 5. Migration Strategy

### Preserved

- `/api/activities*`
- `/api/tracking*`
- `/api/digests*`
- `/api/analysis*`
- existing opportunity workbench pages
- legacy opportunity tables

### Added

- `/api/agent/*`
- `/api/product-selection/*`
- shared agent tables
- product-selection tables
- `/agent`
- `/selection/*`

### Explicit compatibility rules

- old routes remain supported
- old tables remain readable
- new tables are additive
- product selection is isolated from `Activity`

## 6. Resulting System Shape

The system is now best understood as:

`shared agent platform + opportunity domain + product-selection domain`

not as:

`one giant activity system with more fields`

That distinction matters because future domains can now be added by plugging new tools and repositories into the same shared platform.

## 7. Recommended Next Steps

### Short term

- add live marketplace adapters behind the current selection service boundary
- expand smoke coverage across both domains
- add richer artifact deep links and follow-up actions

### Medium term

- extract more legacy business logic out of `data_manager.py`
- promote the shared agent platform into the primary interaction layer
- standardize more AI behaviors behind platform-level orchestration

### Long term

- move from SQLite to a stronger multi-domain persistence setup when throughput requires it
- add more bounded contexts on top of the same shared agent platform

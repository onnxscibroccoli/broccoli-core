# Knowledge References (Static Catalog)

Curated, high-signal external repositories relevant to Broccoli Core.

## Purpose

Provide the Adaptive Planner and Knowledge Graph with a small, intentional
set of prior-art references. Not a dump of starred repos.

## Scope (Phase A)

Static YAML catalogs only. Zero runtime cost.

| File | Domain |
|------|--------|
| android-automation.yaml | Termux, accessibility, device control, Appium |
| agent-frameworks.yaml | Multi-agent runtimes, orchestration, autonomy patterns |
| memory-systems.yaml | Agent memory, knowledge graphs, persistent context |
| agent-compute.yaml | Durable agent workspaces / virtual computers |

## Entry schema

- repo: owner/name
  url: https://github.com/owner/name
  why: one-line relevance to Broccoli Core
  tags: [list]

## Progression toward C

Tracked in issues 2 and 12:

1. A done — static curated YAMLs in-tree
2. B later — optional star-sync helper that filters a GitHub users stars into these catalogs
3. C target — external knowledge catalog repo and/or durable agent workspace via cloudflare/computer

Do not expand these files into a full Awesome list. Keep entries high-signal only.

---
name: smartmoney-cub-editorial-system
description: SmartMoney-Cub Editorial System — warm, restrained, evidence-driven editorial design language for the read-only trading review harness. Load when producing any SmartMoney-Cub visual artifact (README covers, system diagrams, docs illustrations).
---

# SmartMoney-Cub Editorial System

An original Claude-inspired editorial design language owned by SmartMoney-Cub. It borrows a temperament — warm paper, humanist serif display, restrained single accent, generous whitespace — not any brand asset. Never copy Anthropic/Claude logos, wordmarks, illustrations, or page layouts.

## Personality

editorial · thoughtful · trustworthy · warm technical · evidence-driven · restrained · open-source · human-in-the-loop · local-first · calm intelligence

The artifact should read like a high-quality technical journal or research workbench, never like a finance-app advertisement.

## Tokens

Canonical tokens live in `tokens/colors_and_type.css`. Key relationships:

- Backgrounds are warm paper (`--paper` #F5F0E8, `--paper-light` #FBF8F2). Never dark, never pure white pages.
- Text is warm charcoal (`--ink` #24211D), never #000.
- Terracotta (`--terracotta` #C96F4A) is the only emphasis color: key nodes, step numbers, one primary path. Never large saturated fills.
- Sage (`--sage` #7D8A78) exclusively marks safety / verification / human-confirmation semantics.
- Hairlines use `--line` #D4CCC2 at 1.5px.

## Typography

- Display: humanist serif stack (`--font-display`) for product name and zone titles.
- Body/nodes: modern sans stack (`--font-body`).
- Machine contracts: mono stack (`--font-mono`), always rendered small and quiet.
- Bilingual rule: English is the primary node title, Chinese is a same-meaning subtitle on the next line, at roughly 80% of the English size but never below 21px on flow canvases. Max two text layers per node.
- Casing: sentence case for descriptions; product name in original casing; small caps/uppercase only for micro-labels (tracking +0.08em).

## Component language

- Paper cards with `--radius-card` (10px), whisper shadows or none.
- 1.5px hairline connectors; arrowheads small and filled with `--ink-muted`.
- Small circled or square step numbers in terracotta, mono font.
- Document dog-ears, check ticks, hash marks as provenance/evidence motifs.
- A single visual focus per artifact. Generous margins (min 64px canvas padding).
- Optional paper grain at <= 3% opacity, never behind small text.

## Forbidden

Glassmorphism, neon glow, 3D coins, bull/bear animals, candlestick charts as hero subject, AI brains, robot mascots, cute cub mascots, cyberpunk, broker dashboards, dense data walls, exaggerated profit curves, "AI stock picking" implications, blue-purple neon gradients, rainbow gradients.

## Safety framing

Every public artifact carries the read-only boundary, quiet but present:

- Human line: "NO ORDER · NO CANCEL · NO TRADE / 不下单 · 不撤单 · 不自动交易"
- Machine line (mono): `READ_ONLY_NO_ORDER_NO_CANCEL_NO_TRADE`

The safety line must never be visually louder than the product name. Never a red warning banner; use sage or muted ink.

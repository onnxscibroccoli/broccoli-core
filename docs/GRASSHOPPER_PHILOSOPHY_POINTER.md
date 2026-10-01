# Grasshopper philosophy pointer

Broccoli Core is the device executor and the older philosophy source. It is not the control plane.

The knowledge graph and the implementation philosophy derived from the helpful older layer now live in Grasshopper:

- `docs/BROCCOLI_KNOWLEDGE_GRAPH.md` (`BROCCOLI-KG-2026-10-01`)
- `docs/BROCCOLI_IMPLEMENTATION_PHILOSOPHY.md`

Adopt from this repo:

- `docs/ROADMAP.md` principles
- `docs/VISION.md` inversion
- `docs/INTENT_AUTOMATION_NORTH_STAR.md` cheap cascade
- `docs/KERNEL.md` and `runtime/kernel.py` atom
- `INSTRUCTIONS.md` phone-closes-its-own-loop contract
- `lib/rish_run.sh` called with `RISH_PRESERVE_ENV=0`

Do not adopt the root log pile, `advance_step*.sh`, or docs that only say "see chat."

Do not modify `lib/rish_run.sh` or `lib/rish_cmd.sh` from a Grasshopper transport failure.

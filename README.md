# MTG deterministic baseline policy

This repository contains an engine-agnostic Python policy for choosing among
already-legal, structured MTG actions. It has no Forge imports and does not
determine legality. A future adapter is responsible for converting engine state
and legal actions into the immutable types in `mtg_agent.policy.models`.

Each evaluator is a pure deterministic heuristic. The policy sums its raw
contributions into these components:

`immediate_value + board_value + card_advantage + tempo + mana_efficiency + interaction_value - risk - future_opportunity_cost`

Each component is multiplied by its configured non-negative weight. Every
candidate and its evaluator breakdown is retained in a JSON-serializable
`ScoringRecord`. Exact score ties select the lexicographically smallest stable
`action_id`; input order never affects the result. Pass is represented by
`ActionType.PASS`, receives a normal score, and may be selected.

## Forge smoke runner

The runner uses a tested Forge 2.0.14 patch over the desktop `sim` entry point:

```sh
python -m engine.runner \
  --deck decks/dimir_midrange/main.txt \
  --opponent decks/opponents/izzet_spellementals.txt \
  --games 1 \
  --seed 12345 \
  --play
```

The Forge distribution is intentionally ignored by Git. Its expected artifact,
version, local patch, and patched checksum are recorded in
`engine/forge/manifest.json`. The patch fixes Teamwork total-power cost
preflight and adds explicit starting-player control. Build it with
`engine/forge/build_patched_2_0_14.sh /path/to/forge-2.0.14-source`, install it
at `engine/forge/dist/2.0.14`, or set `MTG_FORGE_HOME`.

Forge's stock simulation output does not expose opening hands, every game-state
snapshot, or every legal action. The runner persists all available mulligan,
turn, phase, and selected game-log action events as JSONL and explicitly marks
unavailable fields and `trajectory_capture_complete` as `false`.

The exact Izzet sideboard transform is stored in
`data/sideboarding/izzet_spellementals.json`. Reproducible sequential
experiments can be run with:

```sh
python -m engine.runner.experiment \
  --output-dir results/izzet_spellementals \
  --games-per-stage 20 \
  --first-seed 2026083001
```

Run the focused suite with:

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
```

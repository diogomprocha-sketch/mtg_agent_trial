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

The runner uses Forge 2.0.14's verified desktop `sim` entry point:

```sh
python -m engine.runner \
  --deck decks/dimir_midrange/main.txt \
  --opponent decks/opponents/izzet_spellementals.txt \
  --games 1 \
  --seed 12345
```

The Forge distribution is intentionally ignored by Git. Its expected artifact,
version, and checksum are recorded in `engine/forge/manifest.json`; install it at
`engine/forge/dist/2.0.14` or set `MTG_FORGE_HOME`. The runner stores the raw
Forge log and a structured result under `results/`.

Forge's stock simulation output does not expose opening hands, every game-state
snapshot, or every legal/chosen action. Results therefore explicitly set
`trajectory_capture_complete` to `false`; they must not be treated as complete
training trajectories or used to start a large experiment.

Run the focused suite with:

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
```

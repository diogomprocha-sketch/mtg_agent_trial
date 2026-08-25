# Dimir Midrange vs Izzet Spellementals

All results below were produced by local Forge 2.0.14+mtg-agent.1 games.
The sample contains 40 completed games and
0 failed games. Failed games are excluded from rates.

| Slice | Games | Wins | Losses | Win rate |
| --- | ---: | ---: | ---: | ---: |
| Overall | 40 | 25 | 15 | 62.5% |
| Pre-board | 20 | 12 | 8 | 60.0% |
| Post-board | 20 | 13 | 7 | 65.0% |
| Play | 20 | 11 | 9 | 55.0% |
| Draw | 20 | 14 | 6 | 70.0% |

- Mulligan rate: 20.0%
- Average game length: 21.35 turns
- Sideboard impact: 5.0%
- Overall 95% Wilson interval: [0.47032439137301096, 0.7577702083276673]

## Common logged action patterns

Winning games: `[('Add To Stack: Ai(1)-Dimir Midrange activated Kaito, Bane of Nightmares', 67), ('Add To Stack: Ai(1)-Dimir Midrange cast Spyglass Siren', 43), ('Add To Stack: Ai(2)-Izzet Spellementals cast Sleight of Hand', 41), ('Land: Ai(2)-Izzet Spellementals played Island', 41), ('Add To Stack: Ai(1)-Dimir Midrange triggered Spyglass Siren', 40)]`

Losing games: `[('Land: Ai(2)-Izzet Spellementals played Island', 38), ('Add To Stack: Ai(2)-Izzet Spellementals cast Winternight Stories', 34), ('Add To Stack: Ai(2)-Izzet Spellementals cast Opt', 33), ('Add To Stack: Ai(2)-Izzet Spellementals cast Prismari Charm', 33), ('Add To Stack: Ai(1)-Dimir Midrange activated Restless Reef', 33)]`

## Trajectory limitation

Forge 2.0.14's stock game log does not expose opening-hand identities, complete
state snapshots, or complete legal-action sets. The JSONL trajectories preserve
all available turn, phase, mulligan, and selected game-log action events and mark
the unavailable fields explicitly. They are not labeled complete trajectories.

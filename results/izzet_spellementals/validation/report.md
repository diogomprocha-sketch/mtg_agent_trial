# Dimir Midrange vs Izzet Spellementals

All results below were produced by local Forge 2.0.14+mtg-agent.1 games.
The sample contains 4 completed games and
0 failed games. Failed games are excluded from rates.

| Slice | Games | Wins | Losses | Win rate |
| --- | ---: | ---: | ---: | ---: |
| Overall | 4 | 2 | 2 | 50.0% |
| Pre-board | 2 | 1 | 1 | 50.0% |
| Post-board | 2 | 1 | 1 | 50.0% |
| Play | 2 | 2 | 0 | 100.0% |
| Draw | 2 | 0 | 2 | 0.0% |

- Mulligan rate: 0.0%
- Average game length: 19.00 turns
- Sideboard impact: 0.0%
- Overall 95% Wilson interval: [0.15003898915214947, 0.8499610108478506]

## Common logged action patterns

Winning games: `[['Add To Stack: Ai(1)-Dimir Midrange activated Kaito, Bane of Nightmares', 8], ['Add To Stack: Ai(1)-Dimir Midrange cast Spyglass Siren', 6], ['Add To Stack: Ai(1)-Dimir Midrange triggered Spyglass Siren', 6], ['Add To Stack: Ai(1)-Dimir Midrange activated Map Token targeting [Spyglass Siren]', 4], ['Land: Ai(1)-Dimir Midrange played Gloomlake Verge', 4]]`

Losing games: `[['Add To Stack: Ai(1)-Dimir Midrange activated Restless Reef', 12], ['Add To Stack: Ai(1)-Dimir Midrange triggered Restless Reef targeting [Ai(2)-Izzet Spellementals]', 7], ['Land: Ai(2)-Izzet Spellementals played Steam Vents', 6], ['Add To Stack: Ai(2)-Izzet Spellementals cast Eddymurk Crab', 6], ['Add To Stack: Ai(2)-Izzet Spellementals cast Opt', 5]]`

## Trajectory limitation

Forge 2.0.14's stock game log does not expose opening-hand identities, complete
state snapshots, or complete legal-action sets. The JSONL trajectories preserve
all available turn, phase, mulligan, and selected game-log action events and mark
the unavailable fields explicitly. They are not labeled complete trajectories.

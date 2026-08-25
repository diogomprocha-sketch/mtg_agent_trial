# MTG Agent Engineering Rules

This project is a research-grade Magic: The Gathering Standard agent.

## Never

- Invent card text.
- Invent decklists.
- Silently substitute cards.
- Silently change decklists.
- Claim simulation results that were not actually run.
- Mix training and evaluation games.
- Report small samples as statistically meaningful.
- Hard-code matchup results.
- Hide Forge compatibility problems.

## Always

- Preserve exact decklists.
- Record source and date for external decklists.
- Record random seeds.
- Make experiments reproducible.
- Write tests for rules-sensitive behavior.
- Log complete trajectories.
- Distinguish measured results from hypotheses.
- Report sample size.
- Report uncertainty.
- Keep the game engine and policy separate.

## Unsupported cards or Forge features

When a card or Forge feature is unsupported:

1. Identify the exact incompatibility.
2. Create a test reproducing it.
3. Do not substitute another card.
4. Report the problem clearly.
5. Implement a compatibility layer only if the real card behavior can be
   preserved.

## Experiment records

Every experiment must record:

- Configuration.
- Seed.
- Decklist hashes.
- Opponent-list hashes.
- Engine version.
- Agent version.
- Result.
- Trajectory location.

Reproducibility is more important than speed.

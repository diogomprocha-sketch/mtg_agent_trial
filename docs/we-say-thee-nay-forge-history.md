# Forge history: We Say Thee Nay! (MSH #82)

Research date: 2026-08-25

## Conclusion

Forge first added `We Say Thee Nay!` on 2026-06-16 in commit
`56d2dfedf5a8bc7c6ecdf0d26f35e7eef17c69b0`. The first stable release
containing it is Forge 2.0.13.

The card script is not the source of an undefined `Any` variable. Its only
referenced SVar is `X`, and `SVar:X:Count$Teamwork.4.2` is defined. The
`SVar 'Any' not found` diagnostics come from a mismatch in the generic AI cost
preflight:

1. `CostTeamwork` uses `"Any"` as a sentinel quantity for "tap any number."
2. `ComputerUtilCost.checkTapTypeCost()` handles total-power tap costs only
   when the spell ability is Crew.
3. Teamwork is not Crew, so the preflight treats `"Any"` as an amount
   expression and passes it to `AbilityUtils.calculateAmount()`.
4. `calculateAmount()` attempts an SVar lookup, emits the diagnostics, and
   returns zero.

The actual cost legality and payment paths do recognize the total-power form.
Consequently, the diagnostic is not proof that the card cannot resolve, but
the AI preflight is incorrect and can accept a zero-card approximation of the
Teamwork tap cost.

This defect is present in Forge 2.0.13, Forge 2.0.14, and the inspected
2.0.15-SNAPSHOT source. No first known-good Forge release for **AI use of the
Teamwork branch** was found.

## Source revisions inspected

| Source | Revision | Date | Result |
| --- | --- | --- | --- |
| First card revision | `56d2dfedf5a8bc7c6ecdf0d26f35e7eef17c69b0` | 2026-06-16 | Card added under `cardsfolder/upcoming/` |
| First stable release containing the card | `forge-2.0.13`, commit `852066bf4f761b302ed17cb011999d8a8fe08ad6` | 2026-06-22 | Script and affected AI preflight present |
| Latest stable release | `forge-2.0.14`, commit `a37a865a53280dd8ad6fad3384d69611e8c5a42f` | 2026-08-08 | Same card and Teamwork cost blobs as 2.0.13 |
| Latest snapshot source | `8fa4e6bd3f4dad0eec408db5f59baf883456cb83` (`2.0.15-SNAPSHOT-08.25`) | 2026-08-25 | Same card and Teamwork cost blobs as 2.0.13/2.0.14 |

The annotated release tag objects are
`d61cf138cc0a80bdd71749a05975abdfb68e9818` for `forge-2.0.13` and
`266c96e466895136feb56e26681753f572b6053c` for `forge-2.0.14`.

The current stable release is:
<https://github.com/Card-Forge/forge/releases/tag/forge-2.0.14>.
The daily release channel is:
<https://github.com/Card-Forge/forge/releases/tag/daily-snapshots>.

## Card definition history

### Initial implementation

Commit:
`56d2dfedf5a8bc7c6ecdf0d26f35e7eef17c69b0`
(`MSH Jumpstart et al. batch #11 (#10973)`, 2026-06-16)

Initial path:

```text
forge-gui/res/cardsfolder/upcoming/we_say_thee_nay.txt
```

The complete functional portion was:

```text
Name:We Say Thee Nay!
ManaCost:1 U
Types:Instant Arcane
K:Teamwork:2
A:SP$ Counter | TargetType$ Spell | TgtPrompt$ Select target spell | ValidTgts$ Card | UnlessCost$ X | SpellDescription$ Counter target spell unless its controller pays {2}. Counter that spell unless its controller pays {4} instead if this spell was cast using teamwork.
SVar:X:Count$Teamwork.4.2
```

### Migration

Commit:
`9114727bf0b13419772e29b5e3bee7f6602a0503`
(`Migrate upcoming (#11046)`, 2026-06-19)

The file moved without a content change:

```text
forge-gui/res/cardsfolder/upcoming/we_say_thee_nay.txt
    -> forge-gui/res/cardsfolder/w/we_say_thee_nay.txt
```

`git log --follow` reports no other commits for this card through snapshot
revision `8fa4e6bd3f4dad0eec408db5f59baf883456cb83`.

### Version comparison

The card blob is
`a8e3e9bc48d57abfbb785e6af34f5813705a49fe` in all of:

- the first implementation commit;
- Forge 2.0.13;
- Forge 2.0.14;
- snapshot revision `8fa4e6bd3f4dad0eec408db5f59baf883456cb83`.

Therefore, no older version containing the card has a different card script.
Forge 2.0.12 predates both the card and Teamwork support.

## Teamwork implementation history

The relevant implementation arrived in several commits before the card:

| Commit | Date | Change |
| --- | --- | --- |
| `68ee90b52a025bf14fbfd58f57c4be67737dd00a` | 2026-06-10 | Added `OptionalCost.Teamwork`, converted `Teamwork:N` into a total-power tap cost, and added `Count$Teamwork` handling |
| `670e3e4ad4a1a3edfe56af9eb88d591634ccf26e` | 2026-06-10 | Corrected the card-state check from `isEntwine()` to `isTeamwork()` and added the spell-ability optional-cost check |
| `4870180a514b0baecddb4e824c98d9f3747a437e` | 2026-06-11 | Added `CostTeamwork` and the `Teamwork<N>` cost parser |
| `749bc029ed53c0f6d11a36df4846cc71970be4f2` | 2026-06-11 | Corrected the `CostTeamwork` constructor signature to match its parser |
| `cb8beab2b13799f14a3ef9aae1534672692193ee` | 2026-06-11 | Registered `TEAMWORK` as a `KeywordWithAmount` |

The initial generic representation in
`forge-game/src/main/java/forge/game/GameActionUtil.java` was:

```java
String costString =
    "tapXType<Any/Creature.YouCtrl+withTotalPowerGE" + k[1] + ">";
```

Commit `4870180...` replaced it with:

```java
String costString = "Teamwork<" + k[1] + ">";
```

and introduced
`forge-game/src/main/java/forge/game/cost/CostTeamwork.java`:

```java
public class CostTeamwork extends CostTapType {
    public CostTeamwork(final String amount) {
        super("Any", "Creature.YouCtrl+withTotalPowerGE" + amount, null, false);
    }
}
```

Its blob,
`684bad7ffa9a99de46300dbd1edd40ad98e0287d`, is unchanged in Forge
2.0.13, Forge 2.0.14, and the inspected snapshot.

## SVar analysis

### The card SVar is defined

The card's counter ability uses:

```text
UnlessCost$ X
SVar:X:Count$Teamwork.4.2
```

`forge-game/src/main/java/forge/game/ability/AbilityUtils.java` handles
`Count$Teamwork` by selecting `4` when `OptionalCost.Teamwork` was paid and
`2` otherwise. This is independent of the `"Any"` diagnostic.

There is no `SVar:Any` in the card script, nor should the script need one:
`"Any"` originates in `CostTeamwork`, where it is intended as a quantity
sentinel rather than a card-script variable.

### Exact failing AI path

`forge-ai/src/main/java/forge/ai/ComputerUtilCost.java` contains:

```java
if (sa.isCrew()) {
    // Handles +withTotalPowerGE for Crew.
    ...
}

Integer c = part.convertAmount();
if (c == null) {
    c = AbilityUtils.calculateAmount(source, part.getAmount(), sa);
}
```

For `Teamwork:2`:

```text
part.getAmount() = "Any"
part.getType()   = "Creature.YouCtrl+withTotalPowerGE2"
sa.isCrew()      = false
part.convertAmount() = null
```

The resulting
`AbilityUtils.calculateAmount(source, "Any", sa)` first checks the spell
ability, then the card, and emits:

```text
SVar 'Any' not found in ability, fallback to Card (...)
SVar 'Any' not defined in Card (...)
```

It returns zero rather than throwing. This explains why an AI game can print
the diagnostic and continue.

The problematic generic preflight predates Teamwork. `git blame` attributes
the non-numeric fallback to commit
`b7eaca64836e8f7cf9111ea769cb5bb652ec3955` (2021-08-14,
`Fix TapXType & CostSacrifice payment fails`). The Teamwork implementation
reused that representation without adding the corresponding non-Crew
total-power branch.

### Paths that correctly handle Teamwork

The following paths inspect `+withTotalPowerGE` before interpreting the
quantity:

- `forge-game/src/main/java/forge/game/cost/CostTapType.java`
  - `canPay()` sums the power of eligible untapped creatures.
- `forge-ai/src/main/java/forge/ai/AiCostDecision.java`
  - `visit(CostTapType)` calls
    `ComputerUtil.chooseTapTypeAccumulatePower(...)`.

This is why the warning does not necessarily prevent actual payment.
`ComputerUtilCost.checkTapTypeCost()` lacks the equivalent general branch.

## Can this occur during `sim`?

Yes. Forge's command-line simulation is dispatched by:

```text
forge-gui-desktop/src/main/java/forge/view/Main.java
    -> forge.view.SimulateMatch.simulate(...)
```

`SimulateMatch` creates AI players and starts ordinary `Match` games. It does
not provide a separate rules implementation for this card. The same AI code
used by other AI games evaluates and pays actions.

The direct call site is
`forge-ai/src/main/java/forge/ai/AiController.java`,
`canPlayAndPayForFace()`:

```java
Set<Card> tappedForMana =
    AiCardMemory.getMemorySet(player, MemorySet.PAYS_TAP_COST);
if (tappedForMana != null && !tappedForMana.isEmpty()
        && !ComputerUtilCost.checkTapTypeCost(
            player, sa.getPayCosts(), host, sa,
            new CardCollection(tappedForMana))) {
    return AiPlayDecision.CantAfford;
}
```

Thus the diagnostic can occur in `sim` when the considered spell ability
contains the Teamwork optional cost and the AI's tap-cost memory is nonempty.
It is not exclusive to the CLI simulator; normal AI play shares the path.

Related AI behavior:

- `forge-ai/src/main/java/forge/ai/SpellAbilityAi.java`
  `chooseOptionalCosts()` currently chooses any optional cost that
  `ComputerUtilCost.canPayCost()` says is payable. It has no
  Teamwork-specific value decision.
- `forge-ai/src/main/java/forge/ai/AiCostDecision.java` can select creatures
  whose accumulated power pays the cost.
- `forge-ai/src/main/java/forge/ai/ComputerUtilCost.java` performs the
  inconsistent preflight described above.

The only `SimulateMatch.java` changes after Teamwork was added were unrelated:

- `ff6d1667e7dc7d334e1e4abfbeaaad58701a7c15` added the simulation seed option.
- `0acfa8f724ec7b9752431e7a8b0cf4f95626d023` added per-player AI profiles.

## Release assessment

| Version | Card available | Ordinary counter mode | Teamwork rules path | AI preflight diagnostic |
| --- | --- | --- | --- | --- |
| 2.0.12 | No | N/A | No Teamwork implementation | N/A |
| Earliest containing revision (`56d2df...`) | Yes, upcoming | Script present | Current representation already present | Present |
| 2.0.13 | Yes | Scripted | Cost legality/payment handlers present | Present |
| 2.0.14 | Yes | Observed in a real `sim` game | Not demonstrated by that game | Present in source |
| 2.0.15-SNAPSHOT-08.25 | Yes | Scripted | Same implementation as 2.0.14 | Present |

Forge 2.0.14 was observed casting `We Say Thee Nay!` in the repository's
seed-12345 reproducibility run, where it countered `Traumatic Critique`.
That event used the ordinary branch; it does not establish that the Teamwork
branch is correct.

Accordingly:

- **First release containing the card:** Forge 2.0.13.
- **First known-good release for ordinary AI casting:** Forge 2.0.14, based
  on the recorded run in this repository. This is an observation, not a claim
  that 2.0.13 fails.
- **First known-good release for AI casting with Teamwork:** none identified.
  Every inspected version has the faulty preflight, and no recorded run proves
  correct Teamwork payment plus the `{4}` counter result.

## Evidence locations

Repository simulation evidence:

```text
results/20260825T202833Z-620221a1.forge.log
results/20260825T202854Z-85bcbb72.forge.log
results/seed-12345-reproducibility.json
```

The two logs record the same seeded ordinary-mode cast. They do not contain
the `SVar 'Any'` diagnostic because Teamwork was not used in that event.

No Forge source or card files were modified as part of this investigation.

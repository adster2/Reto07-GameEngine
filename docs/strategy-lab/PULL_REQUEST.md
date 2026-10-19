The accepted browser game and engine need an isolated place to investigate
strategic strength without changing the presentation version. This branch adds
a Python strategy laboratory while preserving all files from `consegna-v1.0`
and the existing Pages branch.

The lab exposes public-information hand beliefs, including the fourteen excluded
tiles and forced-pass constraints, and adds single-observer ISMCTS with actor-local
rollout policies. Tactical features cover heavy doubles, diversity, bridges,
strong numbers, pass pressure and blocked-hand pip outcomes. Sampled-hand
alpha-beta minimax is retained as an explicitly approximate comparison.

CLI inspection, ranking, a separate desktop controller, paired tournaments and
an independent evidence auditor reuse the accepted rules and event protocol.
The research MCTS levels control explicit tree depth; complete-game rollouts
are evaluation and differ from the accepted difficulty semantics. No research
code is published to the live game.

Validation: 70 passing Python tests, three full Linux GUI games, and 1,344
held-out games with zero rule violations and independently audited replays.
Match points are 49.11% against legacy level 2, 52.23% against legacy level 3,
53.42% against greedy, and 68.15% against random. The intervals against the
legacy engines include 50%, so this candidate is not promoted to the live game.

Measured outcomes and limitations:
[RESULTS.md](https://github.com/adster2/Reto07-GameEngine/blob/experiment/strategy-lab/docs/strategy-lab/RESULTS.md).
The lab is a draft research candidate; it must not be presented as an unbeatable
or calibrated AI.

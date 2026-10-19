"""Human domino principles expressed as conditional, public-information features."""
from dataclasses import dataclass
from math import comb

from domino_engine.rules import place
from .belief import BeliefState
from .heuristic import features


@dataclass(frozen=True)
class TacticalWeights:
    shed_pips: float = 1.2
    double_exit: float = 1.5
    mobility: float = 4.0
    reachable: float = 2.0
    strong_ends: float = 2.0
    diversity: float = .75
    lost_bridges: float = 7.0
    pass_pressure: float = 18.0
    block_outcome: float = 400.0


def block_value(candidates,k,ends,own_points):
    """Exact unconditional win-minus-loss mass for a forced block in this model.

    Used when our remaining hand cannot touch either new end. Only hypothetical
    opponent hands with no matching tile lead to two passes. Subset-sum DP counts
    those hands by residual pips, including the zero-point double correctly.
    """
    misses = [t for t in candidates if not any(t.contains(v) for v in ends)]
    if len(misses) < k: return 0.0
    dp = [dict() for _ in range(k+1)]
    dp[0][0] = 1
    for tile in misses:
        for size in range(k,0,-1):
            for points,count in tuple(dp[size-1].items()):
                new = points+tile.points
                dp[size][new] = dp[size].get(new,0)+count
    numerator = sum(count*(1 if points>own_points else -1 if points<own_points else 0)
                    for points,count in dp[k].items())
    return numerator/comb(len(candidates),k)


def score_moves(view,*,exact_blocks=True,weights=TacticalWeights()):
    """Never accepts or reads an actual opponent hand."""
    belief = BeliefState(view)
    before = features(view.hand,view.chain)
    scores,notes = {},{}
    for move in view.legal_moves():
        if move.is_pass:
            scores[move],notes[move] = -500.0,'Passaggio obbligatorio.'
            continue
        remaining = tuple(t for t in view.hand if t!=move.tile)
        if not remaining:
            scores[move],notes[move] = 1000.0,'Chiude immediatamente la mano.'
            continue
        chain = place(view.chain,move)
        ends = (chain[0].left,chain[-1].right)
        after = features(remaining,chain)
        frequencies = [sum(t.contains(v) for t in remaining) for v in range(7)]
        strong = sum(frequencies[v] for v in set(ends))
        diversity = sum(n>0 for n in frequencies)
        bridge_loss = max(0,before['reachable']-after['reachable']-1)
        double_exit = move.tile.points if move.tile.a==move.tile.b else 0
        probability_pass = belief.pass_probability(ends)
        score = (weights.shed_pips*move.tile.points+weights.double_exit*double_exit+
            weights.mobility*after['mobility']+weights.reachable*after['reachable']+
            weights.strong_ends*strong+weights.diversity*diversity-weights.lost_bridges*bridge_loss)
        if after['mobility']:
            score += weights.pass_pressure*probability_pass
        else:
            if exact_blocks:
                value = block_value(belief.candidates,view.opponent_count,ends,after['points'])
            else:
                difference = belief.expected_points()-after['points']
                value = probability_pass*(1 if difference>0 else -1 if difference<0 else 0)
            score += weights.block_outcome*value
        scores[move] = max(-500.0,min(500.0,score))
        notes[move] = (f'Scarica {move.tile.points} punti; mobilità {after["mobility"]}; '
                      f'accesso a {after["reachable"]} tessere; ponti persi {bridge_loss}; '
                      f'P(passo avversario)={probability_pass:.3f} nel modello uniforme.')
    return scores,notes

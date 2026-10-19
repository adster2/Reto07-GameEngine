"""Documented experimental evaluation; coefficients are initial, not trained."""
from dataclasses import dataclass

from domino_engine.rules import place


@dataclass(frozen=True)
class Weights:
    count: float = 36.0
    points: float = 1.2
    mobility: float = 8.0
    reachable: float = 3.0
    support: float = 1.0
    isolated: float = 5.0
    double_risk: float = .6
    tempo: float = 3.0


def features(hand, chain):
    ends = (chain[0].left, chain[-1].right) if chain else None
    frequencies = [sum(t.contains(v) for t in hand) for v in range(7)]
    mobile = sum(ends is None or any(t.contains(v) for v in ends) for t in hand)
    reachable_values = set(ends or range(7))
    while True:
        expanded = reachable_values | {v for t in hand if reachable_values.intersection((t.a,t.b))
                                      for v in (t.a,t.b)}
        if expanded == reachable_values:
            break
        reachable_values = expanded
    reachable = sum(bool(reachable_values.intersection((t.a,t.b))) for t in hand)
    support = sum(n*(n-1)/2 for n in frequencies)
    isolated = sum(all(frequencies[v] == 1 for v in {t.a,t.b}) and
                   ends is not None and not any(t.contains(v) for v in ends) for t in hand)
    double_risk = sum(t.points for t in hand if t.a == t.b and t.a not in reachable_values)
    return {'count':len(hand), 'points':sum(t.points for t in hand), 'mobility':mobile,
            'reachable':reachable, 'support':support, 'isolated':isolated, 'double_risk':double_risk}


def hand_value(f, weights):
    return (-weights.count*f['count'] - weights.points*f['points'] + weights.mobility*f['mobility']
            + weights.reachable*f['reachable'] + weights.support*f['support']
            - weights.isolated*f['isolated'] - weights.double_risk*f['double_risk'])


def state_value(state, observer, weights=Weights()):
    if state.terminal:
        return 0.0 if state.winner is None else 1000.0 if state.winner == observer else -1000.0
    own = features(state.hand(observer),state.chain)
    other = features(state.hand(observer.other),state.chain)
    # These are provable outcomes in a hypothetical world, without traversing
    # extra plies: a player on turn can shed its only tile, or both must pass.
    current = own if state.turn == observer else other
    if current['count'] == 1 and current['mobility']:
        return 1000.0 if state.turn == observer else -1000.0
    if own['mobility'] == other['mobility'] == 0:
        return 1000.0 if own['points'] < other['points'] else -1000.0 if own['points'] > other['points'] else 0.0
    value = hand_value(own,weights)-hand_value(other,weights)
    value += weights.tempo if state.turn == observer else -weights.tempo
    return max(-500.0,min(500.0,value))


def public_value(view, belief, move, weights=Weights()):
    """Cheap complete legal fallback; no guessed hand is treated as a fact."""
    hand = view.hand if move.is_pass else tuple(t for t in view.hand if t != move.tile)
    if not hand:
        return 1000.0
    chain = place(view.chain,move)
    own = features(hand,chain)
    # Conservative expected opponent material; stronger structural terms are
    # evaluated symmetrically once the sampled minimax iterations complete.
    value = hand_value(own,weights) + weights.count*view.opponent_count + weights.points*belief.expected_points()
    value += 16.0*belief.pass_probability((chain[0].left,chain[-1].right))
    return max(-500.0,min(500.0,value))

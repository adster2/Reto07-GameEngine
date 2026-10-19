"""The single source of truth for legal moves and immutable transitions."""
from dataclasses import replace
from .tiles import Move, OrientedTile, Side
from .state import Player, PublicEvent, blocked_winner, validate_state


class IllegalMove(ValueError):
    pass


def moves_for(hand, chain, *, terminal=False):
    if terminal:
        return ()
    moves = []
    for tile in sorted(hand):
        orientations = (OrientedTile(tile.a, tile.b),) if tile.a == tile.b else (
            OrientedTile(tile.a, tile.b), OrientedTile(tile.b, tile.a))
        for oriented in orientations:
            # LEFT and RIGHT on an empty table produce the same chain: use RIGHT.
            if not chain:
                moves.append(Move(tile, Side.RIGHT, oriented))
            else:
                if oriented.right == chain[0].left:
                    moves.append(Move(tile, Side.LEFT, oriented))
                if oriented.left == chain[-1].right:
                    moves.append(Move(tile, Side.RIGHT, oriented))
    return tuple(moves) if moves else (Move(),)


def legal_moves(state, player=None):
    player = state.turn if player is None else Player(player)
    if player != state.turn:
        return ()
    return moves_for(state.hand(player), state.chain, terminal=state.terminal)


def place(chain, move):
    if move.is_pass:
        return chain
    return ((move.orientation,) + chain if move.side == Side.LEFT
            else chain + (move.orientation,))


def apply_move(state, move, *, player=None):
    if player is not None and Player(player) != state.turn:
        raise IllegalMove("Wrong turn")
    if state.terminal:
        raise IllegalMove("The game is already finished")
    if move not in legal_moves(state):
        raise IllegalMove("Tile, end, orientation or pass is illegal")
    actor = state.turn
    hands = list(state.hands)
    passes = state.passes + 1 if move.is_pass else 0
    if not move.is_pass:
        hands[actor.index] = tuple(t for t in hands[actor.index] if t != move.tile)
    terminal = not hands[actor.index] or passes == 2
    reason = "empty_hand" if not hands[actor.index] else "blocked" if passes == 2 else None
    winner = actor if reason == "empty_hand" else blocked_winner(hands) if terminal else None
    result = replace(state, hands=tuple(hands), chain=place(state.chain, move),
                     turn=actor.other, passes=passes, terminal=terminal, reason=reason,
                     winner=winner, history=state.history + (PublicEvent(actor, move, state.ends),))
    validate_state(result)
    return result

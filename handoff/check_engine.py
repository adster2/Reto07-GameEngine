"""Run from the checkout root: python -m handoff.check_engine.

No camera, physical tracker, hidden-hand reconstruction or external dependencies.
The second fixture is explicitly a VIRTUAL referee protocol example.
"""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform


ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def check_sources():
    manifest = json.loads((ROOT / "handoff/approved_manifest.json").read_text("utf-8"))
    expected = manifest["sha256_lf"]
    actual_paths = {p.relative_to(ROOT).as_posix()
                    for p in (ROOT / "domino_engine").rglob("*.py")}
    require(actual_paths == set(expected), "Engine module set differs from approved source")
    for relative_path, digest in expected.items():
        contents = (ROOT / relative_path).read_bytes().replace(b"\r\n", b"\n")
        require(hashlib.sha256(contents).hexdigest() == digest,
                f"Engine source differs: {relative_path}")
    return manifest, len(expected)


def check_examples():
    import domino_engine
    from domino_engine import ALL_TILES, Tile, OrientedTile, Side, Player, from_hands
    from domino_engine.events import EventSession, ObservedScene, ObservedTile, ProposalError
    from domino_engine.knowledge import KnowledgeState
    from domino_engine.strategy import SearchConfig, StrategyEngine

    require(Path(domino_engine.__file__).resolve() == ROOT / "domino_engine/__init__.py",
            "Python imported a different domino_engine checkout")
    own = (Tile(0, 0), Tile(0, 6), Tile(1, 2), Tile(2, 3),
           Tile(3, 3), Tile(4, 5), Tile(5, 6))

    # Public-only production boundary: no opponent hand or excluded tiles supplied.
    view = KnowledgeState(observer=Player.ASSISTED, hand=own, chain=(),
                          turn=Player.ASSISTED, opponent_count=7, history=(),
                          passes=0, terminal=False, winner=None, reason=None)
    before = view.to_dict()
    ranking = StrategyEngine(SearchConfig(level=2)).rank(view)
    require(view.to_dict() == before, "Ranking changed its input")
    require({row.move for row in ranking.moves} == set(view.legal_moves()),
            "Ranking does not cover legal moves")
    require(len(ranking.moves) == len(view.legal_moves()), "Duplicate ranked moves")
    require(ranking.recommendation in view.legal_moves(), "Illegal recommendation")
    require(ranking.diagnostics.limit != "inconsistent_knowledge", "Inconsistent fixture")

    # VIRTUAL TEST ONLY: this referee knows both hands; do not use it with a camera.
    other = tuple(t for t in ALL_TILES if t not in own)[:7]
    initial = from_hands(own, other, turn=Player.ASSISTED)
    session = EventSession(initial)
    scene = ObservedScene((ObservedTile(0, 6, Side.RIGHT,
                                      OrientedTile(0, 6), confidence=0.95),))
    proposal = session.observe(scene)
    require(proposal is not None and proposal.legal, "Valid observation rejected")
    require(session.state == initial and session.revision == 0,
            "Observation changed authoritative state")
    state = session.commit(proposal.id)
    require(state.chain == (OrientedTile(0, 6),), "Wrong confirmed chain")
    require(len(state.hand(Player.ASSISTED)) == 6, "Own hand not updated")
    require(session.commit(proposal.id) == state and session.revision == 1
            and len(session.events) == 1, "Commit is not idempotent")
    require(EventSession.from_json(session.to_json()).state == state, "Replay differs")
    require(session.undo() == initial and session.revision == 2, "Undo differs")
    try:
        session.commit(proposal.id)
    except ProposalError:
        pass
    else:
        raise RuntimeError("Undone event can still be committed")

    return {
        "public_only_ranking": {
            "status": "PASS", "real_opponent_hand_supplied": False,
            "ranked_moves": len(ranking.moves),
            "recommendation": ranking.recommendation.to_dict(),
            "diagnostics": asdict(ranking.diagnostics),
        },
        "virtual_protocol_fixture": {
            "status": "PASS", "physical_integration": False,
            "checks": ["proposal_does_not_mutate", "explicit_commit", "idempotency",
                       "journal_roundtrip", "undo", "undone_id_rejected"],
        },
    }


def main():
    manifest, count = check_sources()
    examples = check_examples()
    print(json.dumps({
        "status": "PASS", "approved_tag": manifest["approved_tag"],
        "approved_source_commit": manifest["approved_source_commit"],
        "source_files_verified": count, "hash_normalization": "CRLF to LF",
        "python": platform.python_version(), "platform": platform.platform(),
        **examples,
        "physical_camera_test": "NOT_RUN",
    }, indent=2))


if __name__ == "__main__":
    main()

"""Canonical double-six identities and explicit logical orientations."""
from dataclasses import dataclass
from enum import Enum


class Side(str, Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"


@dataclass(frozen=True, order=True)
class Tile:
    a: int
    b: int

    def __post_init__(self):
        if type(self.a) is not int or type(self.b) is not int:
            raise ValueError("Tile faces must be integers")
        if not 0 <= self.a <= 6 or not 0 <= self.b <= 6:
            raise ValueError("Tile faces must be in 0..6")
        if self.a > self.b:
            a, b = self.b, self.a
            object.__setattr__(self, "a", a)
            object.__setattr__(self, "b", b)

    @property
    def points(self):
        return self.a + self.b

    def contains(self, value):
        return value in (self.a, self.b)

    def __str__(self):
        return f"[{self.a}|{self.b}]"

    def to_list(self):
        return [self.a, self.b]


@dataclass(frozen=True)
class OrientedTile:
    left: int
    right: int

    def __post_init__(self):
        Tile(self.left, self.right)

    @property
    def tile(self):
        return Tile(self.left, self.right)

    def __str__(self):
        return f"[{self.left}|{self.right}]"

    def to_list(self):
        return [self.left, self.right]


ALL_TILES = tuple(Tile(a, b) for a in range(7) for b in range(a, 7))


@dataclass(frozen=True)
class Move:
    """A pass has no tile, side or orientation. All three are required for a play."""
    tile: Tile | None = None
    side: Side | None = None
    orientation: OrientedTile | None = None

    def __post_init__(self):
        if self.tile is None:
            if self.side is not None or self.orientation is not None:
                raise ValueError("A pass cannot include placement fields")
        elif (not isinstance(self.tile, Tile) or not isinstance(self.side, Side)
              or not isinstance(self.orientation, OrientedTile)
              or self.orientation.tile != self.tile):
            raise ValueError("Placement requires matching tile, side and orientation")

    @property
    def is_pass(self):
        return self.tile is None

    def to_dict(self):
        if self.is_pass:
            return {"pass": True}
        return {"tile": self.tile.to_list(), "side": self.side.value,
                "orientation": self.orientation.to_list()}

    @classmethod
    def from_dict(cls, data):
        if data.get("pass") is True:
            if set(data) != {"pass"}:
                raise ValueError("Pass has unexpected fields")
            return cls()
        if set(data) != {"tile", "side", "orientation"}:
            raise ValueError("Invalid move fields")
        return cls(Tile(*data["tile"]), Side(data["side"]),
                   OrientedTile(*data["orientation"]))

    def __str__(self):
        return "PASS" if self.is_pass else f"{self.tile} {self.side.value} {self.orientation}"

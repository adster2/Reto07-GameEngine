'use strict';

// Presentation only. Moves and logical face order come from the Python referee.
const TableLayout = (() => {
  const LENGTH = 86, WIDTH = 44, GAP = 4;
  const directions = Object.freeze({right: [1, 0], down: [0, 1], left: [-1, 0], up: [0, -1]});
  const key = move => move.tile.join('-');
  const opposite = name => ({right: 'left', left: 'right', up: 'down', down: 'up'})[name];
  const empty = () => ({tiles: [], connections: [], used: {}, adjusted: false});
  const along = tile => tile.double ? WIDTH / 2 : LENGTH / 2;
  const across = tile => tile.double ? LENGTH / 2 : WIDTH / 2;
  function rect(tile) {
    const horizontal = directions[tile.direction][0] !== 0;
    const x = horizontal ? along(tile) : across(tile);
    const y = horizontal ? across(tile) : along(tile);
    return {left: tile.x - x, right: tile.x + x, top: tile.y - y, bottom: tile.y + y};
  }
  function bounds(layout) {
    if (!layout.tiles.length) return {left: -60, right: 60, top: -50, bottom: 50};
    const boxes = layout.tiles.map(rect);
    return {left: Math.min(...boxes.map(b => b.left)), right: Math.max(...boxes.map(b => b.right)),
      top: Math.min(...boxes.map(b => b.top)), bottom: Math.max(...boxes.map(b => b.bottom))};
  }
  function place(layout, move, direction) {
    if (!directions[direction] || move.pass) return null;
    const left = move.side === 'LEFT', vector = directions[direction];
    const tile = {key: key(move), faces: move.orientation.slice(), x: 0, y: 0,
      direction: left && layout.tiles.length ? opposite(direction) : direction,
      double: move.tile[0] === move.tile[1]};
    let connection = null;
    if (layout.tiles.length) {
      const previous = layout.tiles[left ? 0 : layout.tiles.length - 1];
      const outward = left ? opposite(previous.direction) : previous.direction;
      if (direction === opposite(outward)) return null;
      const oldVector = directions[outward];
      const straight = direction === outward;
      const faceOffset = straight || previous.double ? 0 : LENGTH / 4;
      const edge = straight ? along(previous) : across(previous);
      const start = {x: previous.x + oldVector[0] * faceOffset + vector[0] * edge,
        y: previous.y + oldVector[1] * faceOffset + vector[1] * edge};
      tile.x = start.x + vector[0] * (GAP + along(tile));
      tile.y = start.y + vector[1] * (GAP + along(tile));
      connection = {from: start, to: {x: tile.x - vector[0] * along(tile), y: tile.y - vector[1] * along(tile)}};
      const box = rect(tile);
      if (layout.tiles.some(other => {
        const b = rect(other);
        return box.left < b.right + 2 && box.right > b.left - 2 &&
          box.top < b.bottom + 2 && box.bottom > b.top - 2;
      })) return null;
    }
    return {tiles: left ? [tile, ...layout.tiles] : [...layout.tiles, tile],
      connections: connection ? [...layout.connections, connection] : layout.connections.slice(),
      used: {...layout.used, [tile.key]: direction}, adjusted: layout.adjusted};
  }
  function options(layout, move) {
    if (move.pass) return [];
    const end = layout.tiles[move.side === 'LEFT' ? 0 : layout.tiles.length - 1];
    const straight = end ? (move.side === 'LEFT' ? opposite(end.direction) : end.direction) : 'right';
    const candidates = Object.keys(directions).flatMap(direction => {
      const next = place(layout, move, direction);
      if (!next) return [];
      const b = bounds(next), width = b.right - b.left, height = b.bottom - b.top;
      // Keep a compact table; turn before a long row becomes tiny on a phone.
      const overflow = Math.max(0, width - 520) + Math.max(0, height - 350);
      return [{direction, layout: next, compact: width <= 520 && height <= 350,
        score: !layout.tiles.length ? (direction === 'right' ? 0 : 1) :
          overflow * 1000 + Math.max(width / 520, height / 350) * 2 +
          width * height / 100000 + (direction === straight ? 0 : .08)}];
    }).sort((a, b) => a.score - b.score);
    // When there is room to bend, do not offer an ever longer column or row
    // that would make the entire table unreadably small after fitting it.
    const compact = candidates.filter(c => c.compact);
    return compact.length ? compact : candidates;
  }
  function history(events, preferences = {}, straight = false) {
    let layout = empty();
    for (const {move} of events) {
      if (move.pass) continue;
      const name = straight ? (move.side === 'LEFT' && layout.tiles.length ? 'left' : 'right') : preferences[key(move)];
      const candidates = options(layout, move);
      const chosen = candidates.find(c => c.direction === name) || candidates[0];
      if (!chosen) {
        // A hand-arranged spiral can surround an end. A legal move must remain
        // playable: fall back to a clear row, without changing any game state.
        const fallback = history(events, {}, true);
        fallback.adjusted = true;
        return fallback;
      }
      layout = chosen.layout;
      if (name && name !== chosen.direction) layout.adjusted = true;
    }
    return layout;
  }
  function prepare(events, preferences, move) {
    let layout = history(events, preferences);
    let choices = options(layout, move);
    if (!choices.length && !move.pass) {
      layout = history(events, {}, true);
      layout.adjusted = true;
      choices = options(layout, move);
    }
    return {layout, choices};
  }
  function endpoint(tile, left) {
    const vector = directions[left ? opposite(tile.direction) : tile.direction];
    return {x: tile.x + vector[0] * (along(tile) + 24), y: tile.y + vector[1] * (along(tile) + 24)};
  }
  function cleanPreferences(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
    return Object.fromEntries(Object.entries(value).filter(([k, v]) => /^[0-6]-[0-6]$/.test(k) &&
      k[0] <= k[2] && Object.hasOwn(directions, v)));
  }
  return Object.freeze({directions, key, opposite, rect, bounds, place, options, history, prepare, endpoint, cleanPreferences});
})();

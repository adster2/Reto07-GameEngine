'use strict';
const byId = id => document.getElementById(id);
const pipPositions = [[],[4],[0,8],[0,4,8],[0,2,6,8],[0,2,4,6,8],[0,2,3,5,6,8]];
let state = null, busy = true, currentCommand = 'init', cpuPaused = false;
let worker, sequence = 0, ready = false;
const waiting = new Map();
let boardPreferences = {}, pendingVisual = null;
const poseLabels = {right: '→ Destra', down: '↓ Basso', left: '← Sinistra', up: '↑ Alto'};

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function domino(faces, vertical = false) {
  const tile = element('span', 'domino ' + (vertical ? 'vertical' : 'horizontal'));
  tile.setAttribute('role', 'img');
  tile.setAttribute('aria-label', `Tessera ${faces[0]} e ${faces[1]}`);
  for (const value of faces) {
    const face = element('span', 'face');
    face.setAttribute('aria-hidden', 'true');
    for (let position = 0; position < 9; position++) {
      face.append(element('i', pipPositions[value].includes(position) ? 'pip' : 'pip empty'));
    }
    tile.append(face);
  }
  return tile;
}
function describe(move) {
  if (move.pass) return 'Passaggio';
  return `[${move.tile.join('|')}] a ${move.side === 'LEFT' ? 'sinistra' : 'destra'} (${move.orientation.join('|')})`;
}
function showError(message) {
  byId('error').textContent = message;
  byId('error').hidden = !message;
}
function fatal(message) {
  ready = false;
  byId('loading').hidden = false;
  byId('loading-text').textContent = 'Il gioco non è riuscito a completare il caricamento. Controlla la connessione e riprova.';
  byId('retry').hidden = false;
  byId('loading').querySelector('.spinner').hidden = true;
  showError(message);
}
function rpc(request) {
  return new Promise((resolve, reject) => {
    const id = ++sequence;
    const timeout = setTimeout(() => {
      waiting.delete(id);
      reject(new Error('Il motore non ha risposto. Ricarica la pagina per ricominciare.'));
    }, 45000);
    waiting.set(id, {resolve, reject, timeout});
    worker.postMessage({id, request});
  });
}
function randomSeed() {
  const number = new Uint32Array(1);
  crypto.getRandomValues(number);
  return number[0];
}
function canSchedule(command, token) {
  return state && state.token === token && !busy && !state.pending && !state.view.terminal &&
    (command === 'cpu' ? state.view.turn === 'OPPONENT' && !cpuPaused :
      state.view.turn === 'ASSISTED' && byId('show-advice').checked && !state.ranking.length);
}
function scheduleDecision() {
  if (!state || state.pending || state.view.terminal) return;
  const token = state.token;
  const command = state.view.turn === 'OPPONENT' ? 'cpu' : 'rank';
  setTimeout(() => { if (canSchedule(command, token)) run(command); }, 140);
}
async function run(command, data = {}) {
  if (busy || !ready) return null;
  busy = true;
  currentCommand = command;
  showError('');
  render();
  try {
    const reply = await rpc({command, token: state?.token, ...data});
    if (command === 'save') return reply;
    if (command === 'confirm' && pendingVisual?.id === state.pending?.id) {
      boardPreferences = {...pendingVisual.layout.used};
    }
    if (command === 'new_game') boardPreferences = {};
    if (command === 'load') boardPreferences = TableLayout.cleanPreferences(data.table_layout);
    if (command === 'undo') {
      const remaining = new Set(reply.view.chain.map(t => [...t].sort((a,b) => a-b).join('-')));
      boardPreferences = Object.fromEntries(Object.entries(boardPreferences).filter(([key]) => remaining.has(key)));
    }
    state = reply;
    return reply;
  } catch (error) {
    showError(error.message);
    return null;
  } finally {
    busy = false;
    currentCommand = '';
    render();
    scheduleDecision();
  }
}
function renderTable() {
  if (!state) return;
  const pending = state.pending;
  let layout = TableLayout.history(state.view.history, boardPreferences);
  const poseControls = byId('pose-controls');
  poseControls.hidden = !pending?.legal || pending.move.pass;
  poseControls.replaceChildren();
  if (pending?.legal && !pending.move.pass) {
    const prepared = TableLayout.prepare(state.view.history, boardPreferences, pending.move);
    const previous = pendingVisual?.id === pending.id ? pendingVisual.direction : null;
    const selected = prepared.choices.find(c => c.direction === previous) || prepared.choices[0];
    layout = selected.layout;
    pendingVisual = {id: pending.id, direction: selected.direction, layout};
    poseControls.append(element('span', 'pose-label', 'Direzione sul tavolo'));
    for (const [direction, label] of Object.entries(poseLabels)) {
      const choice = prepared.choices.find(c => c.direction === direction);
      const button = element('button', 'pose-button', label);
      button.type = 'button';
      button.setAttribute('aria-label', `Posa verso ${direction === 'up' ? 'l’alto' : direction === 'down' ? 'il basso' : direction === 'left' ? 'sinistra' : 'destra'}`);
      button.setAttribute('aria-pressed', String(selected.direction === direction));
      button.disabled = busy || !choice;
      button.title = choice ? 'Controlla l’anteprima sul tavolo prima di confermare.' : 'Questa direzione non lascia spazio alla tessera o allunga troppo il tavolo.';
      button.addEventListener('click', () => {
        pendingVisual = {id: pending.id, direction, layout: choice.layout};
        renderTable();
      });
      poseControls.append(button);
    }
  } else pendingVisual = null;
  const preview = Boolean(pending?.legal && !pending.move.pass);
  const ends = preview ? pending.new_ends : state.ends;
  byId('left-end').textContent = ends ? ends[0] : '—';
  byId('right-end').textContent = ends ? ends[1] : '—';
  byId('table-hint').textContent = preview ? 'Anteprima: la tessera evidenziata attende conferma. Usa le frecce per cambiare direzione.' :
    layout.adjusted ? 'Il tavolo è stato riordinato per lasciare spazio. S e D indicano le due estremità.' :
    'Le doppie si posano di traverso. S e D indicano le due estremità.';
  const chain = byId('chain');
  if (!layout.tiles.length) {
    const empty = element('p','empty-board','Il tavolo è pronto.');
    empty.append(document.createElement('br'),element('span','','Chi inizia può giocare qualsiasi tessera.'));
    chain.replaceChildren(empty);
    return;
  }
  const bounds = TableLayout.bounds(layout), padding = 48;
  const width = bounds.right - bounds.left + padding * 2;
  const height = bounds.bottom - bounds.top + padding * 2;
  const scale = Math.min(1, Math.max(1, chain.clientWidth - 8) / width, Math.max(1, chain.clientHeight - 8) / height);
  const stage = element('div', 'chain-space');
  stage.style.width = `${width}px`;
  stage.style.height = `${height}px`;
  stage.style.transform = `translate(-50%, -50%) scale(${scale})`;
  const position = node => {
    node.style.left = `${Number(node.dataset.x) - bounds.left + padding}px`;
    node.style.top = `${Number(node.dataset.y) - bounds.top + padding}px`;
  };
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', width); svg.setAttribute('height', height);
  svg.setAttribute('aria-hidden', 'true');
  svg.classList.add('chain-links');
  for (const link of layout.connections) {
    const line = document.createElementNS(svg.namespaceURI, 'line');
    for (const [attribute, value] of Object.entries({x1:link.from.x-bounds.left+padding,y1:link.from.y-bounds.top+padding,
      x2:link.to.x-bounds.left+padding,y2:link.to.y-bounds.top+padding})) line.setAttribute(attribute, value);
    svg.append(line);
  }
  stage.append(svg);
  for (const tile of layout.tiles) {
    const node = domino(tile.faces);
    node.classList.add('board-tile');
    node.dataset.tile = tile.key;
    node.dataset.direction = tile.direction;
    node.dataset.double = String(tile.double);
    node.dataset.x = tile.x; node.dataset.y = tile.y;
    const vector = TableLayout.directions[tile.direction];
    const angle = Math.atan2(vector[1], vector[0]) * 180 / Math.PI + (tile.double ? 90 : 0);
    node.style.transform = `translate(-50%, -50%) rotate(${angle}deg)`;
    if (preview && tile.key === TableLayout.key(pending.move)) {
      node.classList.add('preview-tile');
      node.setAttribute('aria-label', node.getAttribute('aria-label') + ', anteprima da confermare');
    }
    position(node);
    stage.append(node);
  }
  for (const left of [true, false]) {
    const tile = layout.tiles[left ? 0 : layout.tiles.length - 1];
    const point = TableLayout.endpoint(tile, left);
    const badge = element('span', 'chain-end', left ? 'S' : 'D');
    badge.setAttribute('aria-label', left ? 'Estremo sinistro' : 'Estremo destro');
    badge.dataset.x = point.x; badge.dataset.y = point.y;
    position(badge); stage.append(badge);
  }
  chain.replaceChildren(stage);
}
function render() {
  document.body.dataset.busy = String(busy);
  byId('new-game').disabled = !ready || busy;
  if (!state) return;
  const v = state.view, pending = state.pending;
  const human = v.turn === 'ASSISTED';
  const active = human && !v.terminal && !pending && !busy;
  byId('game').hidden = false;
  byId('loading').hidden = true;
  byId('level').value = String(state.level);
  byId('level').disabled = busy || Boolean(pending);
  byId('show-advice').disabled = busy;
  let turn = v.terminal ? 'Manche conclusa' : pending ? (human ? 'Conferma la tua mossa' : 'Conferma la mossa CPU') :
    human ? 'Il tuo turno' : cpuPaused ? 'La CPU attende' : 'La CPU sta pensando';
  if (busy && currentCommand === 'rank') turn = 'Calcolo dei consigli';
  byId('turn').textContent = turn;
  byId('cpu-count').textContent = `${v.opponent_count} ${v.opponent_count === 1 ? 'tessera' : 'tessere'}`;
  const backs = byId('cpu-hand');
  backs.replaceChildren(...Array.from({length: v.opponent_count}, () => element('span','tile-back')));
  backs.setAttribute('aria-label', `${v.opponent_count} tessere coperte`);
  renderTable();
  byId('ply-count').textContent = `${state.event_count} ${state.event_count === 1 ? 'mossa confermata' : 'mosse confermate'}`;
  byId('hand').replaceChildren(...v.hand.map(tile => {
    const button = element('button');
    button.append(domino(tile, true));
    button.setAttribute('aria-label', `Gioca tessera ${tile[0]} e ${tile[1]}`);
    const moves = state.legal_moves.filter(m => !m.pass && m.tile[0] === tile[0] && m.tile[1] === tile[1]);
    button.disabled = !active || !moves.length;
    button.addEventListener('click', () => choosePlacement(moves));
    return button;
  }));
  const points = v.hand.reduce((sum,t) => sum + t[0] + t[1], 0);
  byId('your-points').textContent = `${v.hand.length} tessere · ${points} punti`;
  const mustPass = state.legal_moves.some(m => m.pass);
  byId('hand-hint').textContent = v.terminal ? 'La partita è finita. Puoi iniziarne un’altra.' : !human ?
    'Attendi e conferma la mossa della CPU.' : pending ? 'Controlla la proposta e conferma, oppure scartala.' :
    mustPass ? 'Nessuna tessera è giocabile: devi passare.' : 'Clicca una tessera disponibile e scegli dove giocarla.';
  byId('pass').disabled = !active || !mustPass;
  byId('cpu-play').hidden = human || !cpuPaused || Boolean(pending) || v.terminal;
  byId('cpu-play').disabled = busy;
  byId('undo').disabled = busy || Boolean(pending) || !state.event_count;
  byId('save-game').disabled = busy || Boolean(pending);
  byId('load-game').disabled = busy;
  byId('proposal').hidden = !pending;
  if (pending) {
    byId('proposal-tile').replaceChildren(pending.move.pass ? element('span','avatar','PASS') : domino(pending.move.orientation));
    byId('proposal-actor').textContent = pending.player === 'ASSISTED' ? 'LA TUA PROPOSTA' : 'LA MOSSA DELLA CPU';
    byId('proposal-title').textContent = describe(pending.move);
    byId('proposal-detail').textContent = pending.legal ?
      (pending.new_ends ? `Dopo la conferma, gli estremi saranno ${pending.new_ends.join(' e ')}.` : 'Passaggio obbligatorio, senza pesca.') :
      `Questa mossa non può essere confermata: ${pending.error}`;
    byId('confirm').textContent = pending.player === 'ASSISTED' ? 'Conferma mossa' : 'Conferma mossa CPU';
  }
  byId('confirm').disabled = busy || !pending?.legal;
  byId('discard').disabled = busy || !pending;
  byId('result').hidden = !v.terminal;
  if (v.terminal) {
    byId('result-title').textContent = !v.winner ? 'Pareggio!' : v.winner === 'ASSISTED' ? 'Hai vinto!' : 'Questa volta vince la CPU.';
    const why = v.reason === 'blocked' ? 'La partita si è bloccata dopo due passaggi.' :
      v.winner === 'ASSISTED' ? 'Hai giocato tutte le tue tessere.' : 'La CPU ha giocato tutte le sue tessere.';
    byId('result-text').textContent = `${why} Punti rimasti: tu ${state.result.your_points}, CPU ${state.result.cpu_points}.`;
  }
  byId('history').replaceChildren(...v.history.map(e => element('li','',`${e.player === 'ASSISTED' ? 'Tu' : 'CPU'}: ${describe(e.move)}`)));
  const adviceVisible = byId('show-advice').checked && human && !v.terminal;
  byId('advice').hidden = !adviceVisible;
  byId('ranking').replaceChildren(...state.ranking.map(rank => {
    const row = element('div','rank-row');
    if (!rank.move.pass) row.append(domino(rank.move.orientation));
    const copy = element('div','rank-copy');
    copy.append(element('strong','',describe(rank.move)),element('p','',rank.explanation));
    const score = element('span','rank-score',rank.score.toFixed(2));
    const play = element('button','button','Proponi');
    play.disabled = !active;
    play.addEventListener('click',() => run('propose',{move:rank.move}));
    row.append(copy,score,play);
    return row;
  }));
  if (adviceVisible && !state.ranking.length) byId('ranking').append(element('p','muted','Calcolo dei consigli in corso...'));
  const d = state.cpu_diagnostics || state.advice_diagnostics;
  byId('diagnostics').textContent = d ?
    `Profondità completata ${d.completed_depth}/${d.requested_depth} semimosse; ${d.nodes} nodi, ${d.samples} campioni, ${Math.round(d.elapsed_ms)} ms.` +
      (d.budget_exhausted ? ' Budget raggiunto: è stata usata l’ultima ricerca completa.' : '') : 'Il calcolo comparirà dopo una decisione.';
}
function choosePlacement(moves) {
  if (moves.length === 1) { run('propose',{move:moves[0]}); return; }
  byId('placements').replaceChildren(...moves.map(move => {
    const option = element('button','placement-option');
    option.setAttribute('aria-label',describe(move));
    option.append(element('span','',move.side === 'LEFT' ? 'A sinistra' : 'A destra'),domino(move.orientation));
    option.addEventListener('click', () => {
      byId('placement-dialog').close();
      run('propose',{move});
    });
    return option;
  }));
  byId('placement-dialog').showModal();
}
function openNew() {
  byId('new-level').value = String(state?.level || 3);
  byId('seed').value = '';
  byId('new-dialog').showModal();
}
byId('new-game').addEventListener('click', openNew);
byId('play-again').addEventListener('click', openNew);
byId('close-new').addEventListener('click', () => byId('new-dialog').close());
byId('new-form').addEventListener('submit', async event => {
  event.preventDefault();
  const seed = byId('seed').value === '' ? randomSeed() : Number(byId('seed').value);
  if (!Number.isSafeInteger(seed) || seed < 0) { showError('Scegli un numero intero positivo per la partita.'); return; }
  byId('new-dialog').close();
  cpuPaused = false;
  await run('new_game',{seed,level:Number(byId('new-level').value)});
});
byId('confirm').addEventListener('click', () => { cpuPaused=false; run('confirm',{proposal_id:state.pending.id}); });
byId('discard').addEventListener('click', () => { cpuPaused=true; run('discard'); });
byId('undo').addEventListener('click', () => { cpuPaused=true; run('undo'); });
byId('cpu-play').addEventListener('click', () => { cpuPaused=false; run('cpu'); });
byId('pass').addEventListener('click', () => run('propose',{move:{pass:true}}));
byId('level').addEventListener('change', () => run('set_level',{level:Number(byId('level').value)}));
byId('show-advice').addEventListener('change', () => { render(); scheduleDecision(); });
byId('retry').addEventListener('click', () => location.reload());
byId('save-game').addEventListener('click', async () => {
  const saved = await run('save');
  if (!saved) return;
  const table_layout = TableLayout.history(state.view.history, boardPreferences).used;
  const url = URL.createObjectURL(new Blob([JSON.stringify({format:'reto07-browser-v1',...saved,table_layout},null,2)],{type:'application/json'}));
  const link = element('a'); link.href=url; link.download='reto07-partita.json'; link.click();
  setTimeout(() => URL.revokeObjectURL(url),1000);
});
byId('load-game').addEventListener('click', () => byId('load-file').click());
byId('load-file').addEventListener('change', async event => {
  const file = event.target.files[0];
  if (!file) return;
  if (file.size > 1024*1024) { showError('Il file della partita è troppo grande.'); return; }
  try {
    const saved = JSON.parse(await file.text());
    if (saved.format !== 'reto07-browser-v1') throw new Error('Questo non è un salvataggio del gioco online.');
    cpuPaused = false;
    await run('load',{save:saved.save,level:saved.level,table_layout:TableLayout.cleanPreferences(saved.table_layout)});
  } catch (error) { showError(`Non riesco a leggere la partita: ${error.message}`); }
  event.target.value='';
});
new ResizeObserver(() => renderTable()).observe(byId('chain'));

const version = document.querySelector('meta[name="reto07-build"]')?.content || 'development';
const workerURL = new URL('worker.js',location.href); workerURL.searchParams.set('v',version);
worker = new Worker(workerURL);
const startupTimer = setTimeout(() => fatal('Il caricamento sta impiegando troppo tempo. Riprova.'),120000);
worker.onmessage = async ({data}) => {
  if (data.type === 'status') byId('loading-text').textContent=data.message;
  else if (data.type === 'fatal') { clearTimeout(startupTimer); fatal(data.message); }
  else if (data.type === 'ready') {
    clearTimeout(startupTimer); ready=true; busy=false;
    document.body.dataset.engineReady='true';
    document.body.dataset.sourceCommit=data.source_commit;
    const params=new URLSearchParams(location.search);
    const seedParam=params.get('seed'), level=Number(params.get('level') || 3);
    const seed=seedParam !== null && /^\d+$/.test(seedParam) ? Number(seedParam) : randomSeed();
    await run('new_game',{seed:Number.isSafeInteger(seed) ? seed : randomSeed(),level:[1,2,3,4,5].includes(level)?level:3});
  } else if (data.type === 'reply') {
    const pending=waiting.get(data.id); if (!pending) return;
    clearTimeout(pending.timeout); waiting.delete(data.id);
    if (data.error) {
      const lastLine=data.error.trim().split('\n').at(-1).replace(/^[A-Za-z]+(?:Error|Exception):\s*/, '');
      pending.reject(new Error(lastLine));
    } else pending.resolve(data.result);
  }
};
worker.onerror = () => { clearTimeout(startupTimer); fatal('Il motore del gioco non è disponibile.'); };
worker.postMessage({type:'init'});

/* The referee and Python interpreter live in this worker, never in the renderer.
   Only KnowledgeState-derived replies are posted, except an explicit private save. */
let python;
let queue = Promise.resolve();
const status = (message) => postMessage({type: 'status', message});

async function boot() {
  const response = await fetch(new URL('engine/manifest.json', self.location), {cache: 'no-cache'});
  if (!response.ok) throw new Error('Non riesco a caricare i file del motore. Riprova tra poco.');
  const manifest = await response.json();
  status('Caricamento del motore Python... Il primo avvio può richiedere qualche secondo.');
  importScripts(manifest.runtime + 'pyodide.js');
  python = await loadPyodide({indexURL: manifest.runtime});
  python.FS.mkdirTree('/engine/domino_engine');
  await Promise.all(manifest.files.map(async (file) => {
    const url = new URL('engine/' + file.path, self.location);
    url.searchParams.set('v', file.sha256);
    const res = await fetch(url);
    if (!res.ok) throw new Error('Un file del gioco non è disponibile. Ricarica la pagina.');
    const bytes = await res.arrayBuffer();
    const digest = await crypto.subtle.digest('SHA-256', bytes);
    const hash = [...new Uint8Array(digest)].map(x => x.toString(16).padStart(2,'0')).join('');
    if (hash !== file.sha256) throw new Error('I file del gioco non corrispondono alla versione pubblicata. Ricarica.');
    python.FS.writeFile('/engine/' + file.path, new Uint8Array(bytes));
  }));
  python.runPython('import sys\nsys.path.insert(0, "/engine")\nfrom domino_engine.web_bridge import WebGame\ngame = WebGame()');
  postMessage({type: 'ready', source_commit: manifest.source_commit});
}

self.onmessage = ({data}) => {
  if (data.type === 'init') {
    queue = boot().catch(error => postMessage({type:'fatal', message:String(error.message || error)}));
    return;
  }
  queue = queue.then(() => {
    try {
      if (!python) throw new Error('Il motore non è ancora pronto.');
      python.globals.set('_browser_request', JSON.stringify(data.request));
      const result = JSON.parse(python.runPython('game.handle_json(_browser_request)'));
      postMessage({type:'reply', id:data.id, result});
    } catch (error) {
      postMessage({type:'reply', id:data.id, error:String(error.message || error)});
    } finally {
      if (python) python.globals.delete('_browser_request');
    }
  });
};

// Demo mode (VITE_DEMO=1): runs the same Python rules engine from backend/app
// inside the browser with Pyodide, so the app works as a single static page
// with no server. Message text never leaves the device in this mode.
import analyzer from "../../../backend/app/analyzer.py?raw";
import entities from "../../../backend/app/entities.py?raw";
import llm from "../../../backend/app/llm.py?raw";
import masking from "../../../backend/app/masking.py?raw";
import normalize from "../../../backend/app/normalize.py?raw";
import report from "../../../backend/app/report.py?raw";
import scoring from "../../../backend/app/scoring.py?raw";
import textSignals from "../../../backend/app/text_signals.py?raw";
import urlChecks from "../../../backend/app/url_checks.py?raw";
import domains from "../../../data/official_domains.json?raw";

const PYODIDE = "https://cdn.jsdelivr.net/npm/pyodide@0.26.4/";

// No database in the static demo: no authority-confirmed domains.
const statsStub = "def confirmed_domains():\n    return set()\n";

const files = {
  "/demo/backend/app/__init__.py": "",
  "/demo/backend/app/analyzer.py": analyzer,
  "/demo/backend/app/entities.py": entities,
  "/demo/backend/app/llm.py": llm,
  "/demo/backend/app/masking.py": masking,
  "/demo/backend/app/normalize.py": normalize,
  "/demo/backend/app/report.py": report,
  "/demo/backend/app/scoring.py": scoring,
  "/demo/backend/app/text_signals.py": textSignals,
  "/demo/backend/app/url_checks.py": urlChecks,
  "/demo/backend/app/stats.py": statsStub,
  "/demo/data/official_domains.json": domains,
};

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = src;
    s.onload = resolve;
    s.onerror = reject;
    document.head.appendChild(s);
  });
}

let ready = null;
export function engine() {
  if (!ready) {
    ready = (async () => {
      await loadScript(PYODIDE + "pyodide.js");
      const py = await window.loadPyodide({ indexURL: PYODIDE });
      for (const dir of ["/demo", "/demo/backend", "/demo/backend/app", "/demo/data"]) py.FS.mkdirTree(dir);
      for (const [path, src] of Object.entries(files)) py.FS.writeFile(path, src);
      py.runPython(`
import sys, json
sys.path.insert(0, "/demo/backend")
from app.analyzer import analyse_message
from app.report import build_report
from app.masking import mask

def _check(payload):
    b = json.loads(payload)
    r = analyse_message(b["text"][:5000], lang=b.get("lang", "ar"), use_llm=False)
    r = {k: v for k, v in r.items() if not k.startswith("_")}
    r["saved"] = False
    return json.dumps(r, ensure_ascii=False)

def _report(payload):
    b = json.loads(payload)
    return json.dumps(build_report(mask(b.get("masked_text", "")).text, b.get("urls") or [], b.get("channel"),
                                   b.get("received_at"), b.get("what_happened"), b.get("lang", "ar")), ensure_ascii=False)
`);
      return py;
    })();
    ready.catch(() => { ready = null; });
  }
  return ready;
}

export async function call(fn, body) {
  const py = await engine();
  return JSON.parse(py.globals.get(fn)(JSON.stringify(body)));
}

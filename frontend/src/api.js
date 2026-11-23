const DEMO = import.meta.env.VITE_DEMO === "1";

async function post(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function demo(fn, body) {
  const { call } = await import("./demo/engine.js");
  return call(fn, body);
}

export const checkMessage = (body) => (DEMO ? demo("_check", body) : post("/api/check", body));
export const prepareReport = (body) => (DEMO ? demo("_report", body) : post("/api/report", body));
// Warm up the in-browser engine early in demo mode (it downloads ~10 MB once).
export const warmUp = () => { if (DEMO) import("./demo/engine.js").then((m) => m.engine()).catch(() => {}); };

import { useCallback, useEffect, useState } from "react";
import { ADMIN } from "./adminI18n.js";
import { load, save } from "./storage.js";

const STATUSES = ["high_suspicion", "unclear", "no_visible_indicators"]; // stacked from the baseline up

function readToken() {
  try {
    return window.sessionStorage.getItem("taakkad.adminToken") || "";
  } catch {
    return "";
  }
}
function writeToken(v) {
  try {
    if (v) window.sessionStorage.setItem("taakkad.adminToken", v);
    else window.sessionStorage.removeItem("taakkad.adminToken");
  } catch {
    /* session storage blocked: the token simply isn't remembered */
  }
}

async function api(token, path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...(options.headers || {}) },
  });
  if (res.status === 401) throw new Error("401");
  if (!res.ok) throw new Error(String(res.status));
  return res.json();
}

function Login({ a, onToken, error }) {
  const [value, setValue] = useState("");
  return (
    <main className="card admin-login">
      <h2>{a.loginTitle}</h2>
      <label className="lbl" htmlFor="tok">{a.tokenLabel}</label>
      <input id="tok" className="field" type="password" autoComplete="off" value={value} onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && value && onToken(value.trim())} />
      {error && <p className="err" role="alert">{error}</p>}
      <button className="btn" disabled={!value} onClick={() => onToken(value.trim())}>{a.signIn}</button>
      <p className="muted">{a.tokenHelp}</p>
    </main>
  );
}

function Kpis({ a, s }) {
  const pct = (n) => (s.total ? Math.round((100 * n) / s.total) : 0);
  return (
    <section className="kpis">
      <div className="kpi">
        <span className="kpi-label">{a.total}</span>
        <span className="kpi-value">{s.total.toLocaleString()}</span>
      </div>
      {STATUSES.map((k) => (
        <div key={k} className={`kpi ${k}`}>
          <span className="kpi-label"><span aria-hidden="true">{a.icons[k]}</span> {a.status[k]}</span>
          <span className="kpi-value">{s.by_status[k].toLocaleString()}</span>
          <span className="kpi-sub">{pct(s.by_status[k])}%</span>
        </div>
      ))}
    </section>
  );
}

function shortDay(iso) {
  const [, m, d] = iso.split("-");
  return `${Number(d)}/${Number(m)}`;
}

function DailyChart({ a, daily }) {
  const [hover, setHover] = useState(null);
  const [asTable, setAsTable] = useState(false);
  const W = 640, H = 200, padL = 32, padB = 22, padT = 8;
  const max = Math.max(1, ...daily.map((d) => STATUSES.reduce((t, k) => t + d[k], 0)));
  const nice = Math.max(4, Math.ceil(max / 4) * 4);
  const slot = (W - padL) / daily.length;
  const bw = Math.min(28, slot * 0.62);
  const y = (v) => ((H - padB - padT) * v) / nice;
  const gridVals = [0, nice / 4, nice / 2, (3 * nice) / 4, nice];
  const labelEvery = daily.length > 16 ? 3 : daily.length > 8 ? 2 : 1;

  return (
    <section className="panel">
      <div className="panel-head">
        <h3>{a.dailyTitle}</h3>
        <button className="link-btn" onClick={() => setAsTable(!asTable)}>{asTable ? a.showChart : a.showTable}</button>
      </div>
      <ul className="legend">
        {STATUSES.map((k) => (
          <li key={k}><span className={`swatch ${k}`} aria-hidden="true" />{a.icons[k]} {a.status[k]}</li>
        ))}
      </ul>
      {asTable ? (
        <div className="table-wrap">
          <table>
            <thead><tr><th>{a.day}</th>{STATUSES.map((k) => <th key={k}>{a.status[k]}</th>)}</tr></thead>
            <tbody>
              {daily.map((d) => (
                <tr key={d.day}><td dir="ltr">{d.day}</td>{STATUSES.map((k) => <td key={k}>{d[k]}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="chart-wrap" dir="ltr">
          <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={a.dailyTitle} onMouseLeave={() => setHover(null)}>
            {gridVals.map((g) => (
              <g key={g}>
                <line x1={padL} x2={W} y1={H - padB - y(g)} y2={H - padB - y(g)} className="grid" />
                <text x={padL - 6} y={H - padB - y(g) + 4} className="axis" textAnchor="end">{g}</text>
              </g>
            ))}
            {daily.map((d, i) => {
              const cx = padL + slot * i + slot / 2;
              let base = H - padB;
              const segs = STATUSES.filter((k) => d[k] > 0);
              return (
                <g key={d.day}>
                  {segs.map((k, j) => {
                    const h = Math.max(1, y(d[k]) - (j > 0 ? 2 : 0)); // 2px surface gap between segments
                    const top = base - (j > 0 ? 2 : 0) - h;
                    const isTop = j === segs.length - 1;
                    const r = isTop ? Math.min(4, h, bw / 2) : 0;
                    const x0 = cx - bw / 2, x1 = cx + bw / 2, yb = top + h;
                    const path = `M${x0},${yb} V${top + r} Q${x0},${top} ${x0 + r},${top} H${x1 - r} Q${x1},${top} ${x1},${top + r} V${yb} Z`;
                    base = top;
                    return <path key={k} d={path} className={`bar ${k}`} />;
                  })}
                  {i % labelEvery === 0 && (
                    <text x={cx} y={H - 6} className="axis" textAnchor="middle">{shortDay(d.day)}</text>
                  )}
                  <rect x={cx - slot / 2} y={0} width={slot} height={H - padB} fill="transparent"
                    onMouseEnter={() => setHover(i)} onFocus={() => setHover(i)} tabIndex={0}
                    aria-label={`${d.day}: ${STATUSES.map((k) => `${a.status[k]} ${d[k]}`).join(", ")}`} />
                </g>
              );
            })}
          </svg>
          {hover !== null && (
            <div className="tooltip" style={{ left: `${((padL + slot * hover + slot / 2) / W) * 100}%` }} dir={a.dir}>
              <strong dir="ltr">{daily[hover].day}</strong>
              {STATUSES.map((k) => (
                <span key={k}><span className={`swatch ${k}`} aria-hidden="true" />{a.status[k]}: {daily[hover][k]}</span>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function BarList({ title, rows, empty }) {
  const max = Math.max(1, ...rows.map((r) => r.count));
  return (
    <section className="panel">
      <h3>{title}</h3>
      {rows.length === 0 ? <p className="muted">{empty}</p> : (
        <ul className="barlist">
          {rows.map((r) => (
            <li key={r.key}>
              <span className="bl-label">{r.label}</span>
              <span className="bl-track"><span className="bl-bar" style={{ width: `${(100 * r.count) / max}%` }} /></span>
              <span className="bl-count">{r.count}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Domains({ a, rows, onToggle }) {
  return (
    <section className="panel wide">
      <h3>{a.domainsTitle}</h3>
      <p className="muted">{a.domainsHelp}</p>
      {rows.length === 0 ? <p className="muted">{a.none}</p> : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>{a.domain}</th><th>{a.seen}</th><th>{a.highCount}</th><th>{a.lastSeen}</th><th /></tr>
            </thead>
            <tbody>
              {rows.map((d) => (
                <tr key={d.domain}>
                  <td><code dir="ltr">{d.domain}</code>{d.confirmed && <span className="tag">{a.confirmed}</span>}</td>
                  <td>{d.count}</td>
                  <td>{d.high}</td>
                  <td dir="ltr">{d.last_seen}</td>
                  <td>
                    {d.shortener ? (
                      <span className="muted">{a.shortenerNote}</span>
                    ) : (
                      <button className={d.confirmed ? "btn small outline" : "btn small"} onClick={() => onToggle(d)}>
                        {d.confirmed ? a.unconfirm : a.confirm}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

const EMPTY_ALERT = { title_ar: "", title_en: "", body_ar: "", body_en: "" };

function Alerts({ a, lang, alerts, onPublish, onToggle }) {
  const [form, setForm] = useState(EMPTY_ALERT);
  const ready = Object.values(form).every((v) => v.trim().length >= 2);
  const field = (k, label, multi) => (
    <label className="stack-field">
      <span className="lbl">{label}</span>
      {multi
        ? <textarea rows={2} dir={k.endsWith("ar") ? "rtl" : "ltr"} value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
        : <input className="field" dir={k.endsWith("ar") ? "rtl" : "ltr"} value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />}
    </label>
  );
  return (
    <section className="panel wide">
      <h3>{a.alertsTitle}</h3>
      <p className="muted">{a.alertsHelp}</p>
      <div className="alert-form">
        {field("title_ar", a.alertTitleAr)}
        {field("title_en", a.alertTitleEn)}
        {field("body_ar", a.alertBodyAr, true)}
        {field("body_en", a.alertBodyEn, true)}
      </div>
      <button className="btn" disabled={!ready} onClick={async () => { await onPublish(form); setForm(EMPTY_ALERT); }}>{a.publish}</button>
      <ul className="alert-list">
        {alerts.map((al) => (
          <li key={al.id} className={al.active ? "" : "off"}>
            <div>
              <strong>{al[`title_${lang}`]}</strong>
              <p>{al[`body_${lang}`]}</p>
              <span className="muted" dir="ltr">{al.created_at.replace("T", " ").slice(0, 16)}</span>
            </div>
            <span className={al.active ? "tag neutral" : "tag"}>{al.active ? a.published : a.hidden}</span>
            <button className="btn small outline" onClick={() => onToggle(al)}>{al.active ? a.hide : a.show}</button>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function Admin() {
  const [lang, setLang] = useState(() => load("lang") || "ar");
  const [token, setToken] = useState(readToken);
  const [days, setDays] = useState(14);
  const [data, setData] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState("");
  const a = ADMIN[lang];

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = a.dir;
    document.title = a.title;
  }, [lang, a]);

  const refresh = useCallback(async () => {
    if (!token) return;
    try {
      const [s, al] = await Promise.all([api(token, `/api/admin/stats?days=${days}`), api(token, "/api/admin/alerts")]);
      setData(s);
      setAlerts(al);
      setError("");
    } catch (e) {
      if (e.message === "401") {
        writeToken("");
        setToken("");
        setError(a.badToken);
      } else {
        setError(a.loadError);
      }
    }
  }, [token, days, a]);

  useEffect(() => { refresh(); }, [refresh]);

  const header = (
    <header className="hdr">
      <div>
        <h1>{a.title}</h1>
        <p>{a.sub}</p>
      </div>
      <nav>
        <button className="link" onClick={() => { const l = lang === "ar" ? "en" : "ar"; save("lang", l); setLang(l); }}>
          {lang === "ar" ? "English" : "عربي"}
        </button>
        {token && <button className="link" onClick={() => { writeToken(""); setToken(""); setData(null); }}>{a.signOut}</button>}
      </nav>
    </header>
  );

  if (!token) {
    return (
      <div className="app admin">
        {header}
        <Login a={a} error={error} onToken={(t) => { writeToken(t); setToken(t); setError(""); }} />
      </div>
    );
  }

  const toggleDomain = async (d) => {
    if (d.confirmed) await api(token, `/api/admin/confirmed-domains/${encodeURIComponent(d.domain)}`, { method: "DELETE" });
    else await api(token, "/api/admin/confirmed-domains", { method: "POST", body: JSON.stringify({ domain: d.domain }) });
    refresh();
  };
  const publish = async (form) => {
    await api(token, "/api/admin/alerts", { method: "POST", body: JSON.stringify(form) });
    refresh();
  };
  const toggleAlert = async (al) => {
    await api(token, `/api/admin/alerts/${al.id}/active?active=${!al.active}`, { method: "POST" });
    refresh();
  };

  return (
    <div className="app admin">
      {header}
      <main className="dash">
        <div className="notice">{a.privacyNote}</div>
        {error && <p className="err" role="alert">{error}</p>}
        {data && (
          <>
            {data.synthetic > 0 && <div className="notice warn">{a.syntheticNote(data.synthetic, data.total)}</div>}
            <div className="toolbar">
              <label>
                <span className="lbl">{a.period} </span>
                <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
                  {[7, 14, 30].map((d) => <option key={d} value={d}>{a.days(d)}</option>)}
                </select>
              </label>
              <span className="muted">
                {a.channels}: {Object.entries(data.by_channel).map(([k, v]) => `${a.channel[k] || k} ${v}`).join("، ")}
              </span>
            </div>
            <Kpis a={a} s={data} />
            <DailyChart a={a} daily={data.daily} />
            <div className="grid2">
              <BarList title={a.signalsTitle} empty={a.none}
                rows={data.top_signals.map((r) => ({ key: r.code, label: a.signals[r.code] || r.code, count: r.count }))} />
              <BarList title={a.entitiesTitle} empty={a.none}
                rows={data.top_entities.map((r) => ({ key: r.entity_id, label: r[`name_${lang}`], count: r.count }))} />
            </div>
            {data.top_categories.length > 0 && (
              <BarList title={a.categoriesTitle} empty={a.none}
                rows={data.top_categories.map((r) => ({ key: r.category, label: a.category[r.category] || r.category, count: r.count }))} />
            )}
            <Domains a={a} rows={data.top_domains} onToggle={toggleDomain} />
            <Alerts a={a} lang={lang} alerts={alerts} onPublish={publish} onToggle={toggleAlert} />
          </>
        )}
      </main>
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import { STRINGS } from "./i18n.js";
import { checkMessage, prepareReport, warmUp } from "./api.js";
import { load, save } from "./storage.js";
import { voiceSupported, startVoice } from "./voice.js";

function Header({ t, title, sub, onPrivacy, onLang }) {
  return (
    <header className="hdr">
      <div>
        <h1>{title}</h1>
        <p>{sub}</p>
      </div>
      <nav>
        {onLang && (
          <button className="link" onClick={onLang}>
            {t.dir === "rtl" ? "English" : "عربي"}
          </button>
        )}
        {onPrivacy && (
          <button className="link" onClick={onPrivacy}>
            {t.privacyLink}
          </button>
        )}
      </nav>
    </header>
  );
}

function Partners({ t, large = false }) {
  return (
    <div className={large ? "partners large" : "partners"}>
      <div className="logos">
        <img src="/partners/adpolice.png" alt={t.adPoliceAlt} />
        <img className="wide" src="/partners/42-abudhabi.png" alt={t.fortyTwoAlt} />
      </div>
      <p className="muted" dir={t.dir}>{t.partners}</p>
    </div>
  );
}

function LanguagePick({ onPick }) {
  return (
    <main className="card center">
      <h1 className="brand">تأكّد<br />Ta'akkad</h1>
      <p className="muted">اختر اللغة<br />Choose your language</p>
      <div className="row">
        <button className="btn" onClick={() => onPick("ar")}>عربي</button>
        <button className="btn" onClick={() => onPick("en")}>English</button>
      </div>
      <Partners t={STRINGS.ar} large />
      <p className="muted" dir="ltr">{STRINGS.en.partners}</p>
    </main>
  );
}

function Privacy({ t, firstTime, onAgree, onClose }) {
  const [ok, setOk] = useState(!firstTime);
  return (
    <>
      <Header t={t} title={t.privacyTitle} sub={t.appName} />
      <main className="card">
        <ul className="points">
          {t.privacyPoints.map((p) => <li key={p}>{p}</li>)}
        </ul>
        {firstTime ? (
          <>
            <label className="check">
              <input type="checkbox" checked={ok} onChange={(e) => setOk(e.target.checked)} />
              <span>{t.privacyAgree}</span>
            </label>
            <button className="btn" disabled={!ok} onClick={onAgree}>{t.privacyAgree}</button>
          </>
        ) : (
          <button className="btn outline" onClick={onClose}>{t.privacyClose}</button>
        )}
      </main>
    </>
  );
}

function PublicAlerts({ lang }) {
  const [alerts, setAlerts] = useState([]);
  useEffect(() => {
    warmUp();
    if (import.meta.env.VITE_DEMO === "1") return undefined;
    let alive = true;
    fetch(`/api/alerts?lang=${lang}`)
      .then((r) => (r.ok ? r.json() : []))
      .then((a) => alive && setAlerts(a.slice(0, 3)))
      .catch(() => {});
    return () => { alive = false; };
  }, [lang]);
  if (!alerts.length) return null;
  return (
    <section className="alerts" aria-label="alerts">
      {alerts.map((a) => (
        <div key={a.id} className="alert-public" role="note">
          <strong>⚠ {a.title}</strong>
          <p>{a.body}</p>
        </div>
      ))}
    </section>
  );
}

function CheckForm({ t, lang, draft, setDraft, onResult }) {
  const [busy, setBusy] = useState(false);
  const [ocrBusy, setOcrBusy] = useState(false);
  const [error, setError] = useState("");
  const [recording, setRecording] = useState(null);
  const fileRef = useRef(null);

  async function onImage(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setError("");
    setOcrBusy(true);
    try {
      const { readImage } = await import("./ocr.js"); // loaded only when needed
      const text = await readImage(file);
      if (!text) throw new Error("empty");
      setDraft((d) => ({ ...d, text: d.text ? `${d.text}\n${text}` : text }));
    } catch {
      setError(t.ocrFailed);
    } finally {
      setOcrBusy(false);
    }
  }

  function toggleVoice() {
    if (recording) {
      recording();
      setRecording(null);
      return;
    }
    const stop = startVoice(
      lang,
      (text) => setDraft((d) => ({ ...d, text: d.text ? `${d.text} ${text}` : text })),
      () => setRecording(null),
    );
    setRecording(() => stop);
  }

  async function submit() {
    setBusy(true);
    setError("");
    try {
      const res = await checkMessage({
        text: draft.text.slice(0, 5000),
        lang,
        channel: draft.channel,
        save_consent: draft.saveConsent,
      });
      onResult(res);
    } catch {
      setError(t.error);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="card">
      <PublicAlerts lang={lang} />
      <label className="lbl" htmlFor="msg">{t.messageLabel}</label>
      <textarea
        id="msg"
        dir="auto"
        rows={6}
        maxLength={5000}
        placeholder={t.messagePlaceholder}
        value={draft.text}
        onChange={(e) => setDraft({ ...draft, text: e.target.value })}
      />
      <fieldset className="seg">
        <legend>{t.channelLabel}</legend>
        {["whatsapp", "sms"].map((c) => (
          <label key={c} className={draft.channel === c ? "on" : ""}>
            <input type="radio" name="channel" checked={draft.channel === c} onChange={() => setDraft({ ...draft, channel: c })} />
            {t[c]}
          </label>
        ))}
      </fieldset>
      <div className="row">
        <button className="btn outline" onClick={() => fileRef.current?.click()} disabled={ocrBusy}>
          {ocrBusy ? t.reading : t.attachImage}
        </button>
        <input ref={fileRef} type="file" accept="image/*" hidden onChange={onImage} />
        {voiceSupported && (
          <button className="btn outline" onClick={toggleVoice}>{recording ? t.stopRecord : t.record}</button>
        )}
      </div>
      <label className="check small">
        <input type="checkbox" checked={draft.saveConsent} onChange={(e) => setDraft({ ...draft, saveConsent: e.target.checked })} />
        <span>{t.saveConsent}</span>
      </label>
      {error && <p className="err" role="alert">{error}</p>}
      <button className="btn" onClick={submit} disabled={busy || !draft.text.trim()}>
        {busy ? t.checking : t.check}
      </button>
      <p className="muted center-text">{t.noData}</p>
    </main>
  );
}

function escapeRe(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function Highlighted({ text, words }) {
  const list = words.filter((w) => w && w.trim().length > 1).sort((a, b) => b.length - a.length);
  if (!list.length) return <>{text}</>;
  const re = new RegExp(`(${list.map(escapeRe).join("|")})`, "gi");
  return (
    <>
      {text.split(re).map((part, i) =>
        list.some((w) => w.toLowerCase() === part.toLowerCase()) ? <mark key={i}>{part}</mark> : <span key={i}>{part}</span>,
      )}
    </>
  );
}

function Result({ t, result, onReport, onNew }) {
  const st = t.status[result.status];
  const masked = Object.values(result.masked_counts || {}).reduce((a, b) => a + b, 0);
  return (
    <main className="card">
      <section className={`verdict ${result.status}`} role="status">
        <h2><span aria-hidden="true">{st.icon}</span> {st.label}</h2>
        <p>{result.safe_action}</p>
      </section>

      {result.summary && <p className="summary">{result.summary}</p>}

      {result.reasons.length > 0 && (
        <>
          <h3>{t.why}</h3>
          <ul className="reasons">
            {result.reasons.map((r) => <li key={r.code}>{r.text}</li>)}
          </ul>
        </>
      )}

      {result.checked.length > 0 && (
        <>
          <h3>{t.whatChecked}</h3>
          <ul className="reasons plain">
            {result.checked.map((c) => <li key={c}>{c}</li>)}
          </ul>
        </>
      )}

      <h3>{t.analysedText}</h3>
      <div className="msg" dir="auto">
        <Highlighted text={result.masked_text} words={result.highlights} />
      </div>
      {masked > 0 && <p className="muted">{t.maskedNote(masked)}</p>}

      {result.links.length > 0 && (
        <>
          <h3>{t.links}</h3>
          <ul className="links">
            {result.links.map((l) => (
              <li key={l.url}>
                <code dir="ltr">{l.domain}</code>
                <span className={l.official ? "tag neutral" : "tag"}>{l.official ? t.officialYes : t.officialNo}</span>
              </li>
            ))}
          </ul>
        </>
      )}

      <h3>{t.notGuaranteed}</h3>
      <p className="muted">{result.not_guaranteed}</p>

      <div className="stack">
        {result.status !== "no_visible_indicators" && (
          <button className="btn" onClick={onReport}>{t.report}</button>
        )}
        <button className="btn outline" onClick={onNew}>{t.newCheck}</button>
      </div>
    </main>
  );
}

function Report({ t, lang, result, channel, onBack }) {
  const [what, setWhat] = useState("");
  const [when, setWhen] = useState("");
  const [rep, setRep] = useState(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");

  async function prepare() {
    setError("");
    try {
      const r = await prepareReport({
        masked_text: result.masked_text,
        urls: result.links.map((l) => l.url),
        channel,
        received_at: when ? when.replace("T", " ") : null,
        what_happened: what || null,
        lang,
      });
      setRep(r);
      setCopied(false);
    } catch {
      setError(t.error);
    }
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(rep.report_text);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <main className="card">
      {rep?.bank_first && <div className="bank" role="alert">{rep.bank_first}</div>}
      <fieldset className="radios">
        <legend>{t.whatHappened}</legend>
        {Object.entries(t.happened).map(([k, label]) => (
          <label key={k}>
            <input type="radio" name="what" checked={what === k} onChange={() => setWhat(k)} /> {label}
          </label>
        ))}
      </fieldset>
      <label className="lbl" htmlFor="when">{t.receivedAt}</label>
      <input id="when" type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} />
      <button className="btn" onClick={prepare}>{t.prepare}</button>
      {error && <p className="err" role="alert">{error}</p>}

      {rep && (
        <>
          <textarea readOnly rows={10} dir="auto" value={rep.report_text} />
          <button className="btn outline" onClick={copy}>{copied ? t.copied : t.copy}</button>
          <section className="channel">
            <h3>{t.channelTitle}: {rep.channel.name}</h3>
            <p>{t.channelSteps}</p>
            <a href={rep.channel.info_url} target="_blank" rel="noopener noreferrer">{t.channelInfo}</a>
            <p className="muted">{t.verifiedOn} {rep.channel.verified_on}</p>
            <p className="muted">{t.notSubmitted}</p>
          </section>
        </>
      )}
      <button className="btn outline" onClick={onBack}>{t.back}</button>
    </main>
  );
}

const EMPTY = { text: "", channel: "whatsapp", saveConsent: false };

export default function App() {
  const [lang, setLang] = useState(() => load("lang"));
  const [privacyOk, setPrivacyOk] = useState(() => load("privacyAccepted") === "1");
  const [screen, setScreen] = useState("check");
  const [draft, setDraft] = useState(EMPTY);
  const [result, setResult] = useState(null);

  const t = STRINGS[lang || "ar"];
  useEffect(() => {
    document.documentElement.lang = lang || "ar";
    document.documentElement.dir = t.dir;
    document.title = lang === "en" ? "Ta'akkad — Verify before you act" : "تأكّد — تأكّد قبل لا تضغط";
  }, [lang, t.dir]);

  if (!lang) {
    return <LanguagePick onPick={(l) => { save("lang", l); setLang(l); }} />;
  }
  if (!privacyOk) {
    return <Privacy t={t} firstTime onAgree={() => { save("privacyAccepted", "1"); setPrivacyOk(true); }} />;
  }
  if (screen === "privacy") {
    return <Privacy t={t} firstTime={false} onClose={() => setScreen(result ? "result" : "check")} />;
  }

  const switchLang = () => {
    const l = lang === "ar" ? "en" : "ar";
    save("lang", l);
    setLang(l);
    setResult(null);
    setScreen("check");
  };
  const common = { t, onPrivacy: () => setScreen("privacy"), onLang: switchLang };

  return (
    <div className="app">
      {screen === "check" && (
        <>
          <Header {...common} title={t.appName} sub={t.tagline} />
          <CheckForm t={t} lang={lang} draft={draft} setDraft={setDraft} onResult={(r) => { setResult(r); setScreen("result"); }} />
        </>
      )}
      {screen === "result" && result && (
        <>
          <Header {...common} title={t.resultTitle} sub={t.resultSub} />
          <Result t={t} result={result} onReport={() => setScreen("report")} onNew={() => { setDraft(EMPTY); setResult(null); setScreen("check"); }} />
        </>
      )}
      {screen === "report" && result && (
        <>
          <Header {...common} title={t.reportTitle} sub={t.reportSub} />
          <Report t={t} lang={lang} result={result} channel={draft.channel} onBack={() => setScreen("result")} />
        </>
      )}
      <footer className="muted center-text">
        <Partners t={t} />
        <p>{t.footer}</p>
      </footer>
    </div>
  );
}

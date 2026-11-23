// Optional voice input via the browser's Web Speech API. Some browsers send the
// audio to an external speech service - this is stated on the privacy page.
const Recognition = typeof window !== "undefined" && (window.SpeechRecognition || window.webkitSpeechRecognition);

export const voiceSupported = Boolean(Recognition);

export function startVoice(lang, onText, onEnd) {
  const rec = new Recognition();
  rec.lang = lang === "ar" ? "ar-AE" : "en-US";
  rec.interimResults = false;
  rec.continuous = true;
  rec.onresult = (e) => {
    const text = Array.from(e.results).slice(e.resultIndex).map((r) => r[0].transcript).join(" ");
    onText(text);
  };
  rec.onend = onEnd;
  rec.onerror = onEnd;
  rec.start();
  return () => rec.stop();
}

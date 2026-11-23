// Per-device preferences only (language, privacy acknowledged). Never message content.
export function load(key) {
  try {
    return window.localStorage.getItem(`taakkad.${key}`);
  } catch {
    return null;
  }
}

export function save(key, value) {
  try {
    window.localStorage.setItem(`taakkad.${key}`, value);
  } catch {
    /* private mode etc. - the app still works */
  }
}

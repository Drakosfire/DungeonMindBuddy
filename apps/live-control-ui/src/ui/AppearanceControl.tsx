import { useId, useLayoutEffect, useRef, useState } from "react";

const PRESETS = [
  { id: "default", label: "Buddy" },
  { id: "deep-teal", label: "Deep Teal" },
] as const;

type Preset = (typeof PRESETS)[number]["id"];
const STORAGE_KEY = "buddy.appearance.preset";

function displayPreset(preset: Preset) {
  const root = document.documentElement;
  if (preset === "default") delete root.dataset.buddyTheme;
  else root.dataset.buddyTheme = preset;
}

export function AppearanceControl() {
  const titleId = useId();
  const dialog = useRef<HTMLDialogElement>(null);
  const saved = useRef<Preset>("default");
  const [preview, setPreview] = useState<Preset>("default");

  useLayoutEffect(() => {
    const panel = dialog.current;
    return () => {
      if (panel?.open) displayPreset(saved.current);
    };
  }, []);

  function open() {
    saved.current = document.documentElement.dataset.buddyTheme === "deep-teal" ? "deep-teal" : "default";
    setPreview(saved.current);
    dialog.current?.showModal();
  }

  function select(preset: Preset) {
    setPreview(preset);
    displayPreset(preset);
  }

  function apply() {
    saved.current = preview;
    try {
      if (preview === "default") localStorage.removeItem(STORAGE_KEY);
      else localStorage.setItem(STORAGE_KEY, preview);
    } catch {
      // The current tab can still use the chosen theme.
    }
    dialog.current?.close();
  }

  return <>
    <button className="app-nav-appearance" type="button" onClick={open}>Appearance</button>
    <dialog className="app-appearance" ref={dialog} aria-labelledby={titleId} onClose={() => displayPreset(saved.current)}>
      <h2 id={titleId}>Appearance</h2>
      <fieldset>
        <legend>Theme</legend>
        {PRESETS.map(({ id, label }) => <label key={id}>
          <input type="radio" name={titleId} checked={preview === id} onChange={() => select(id)} />
          {label}
        </label>)}
      </fieldset>
      <div className="app-appearance__actions">
        <button type="button" onClick={() => select("default")} disabled={preview === "default"}>Reset</button>
        <button type="button" onClick={() => dialog.current?.close()}>Cancel</button>
        <button type="button" onClick={apply}>Apply</button>
      </div>
    </dialog>
  </>;
}

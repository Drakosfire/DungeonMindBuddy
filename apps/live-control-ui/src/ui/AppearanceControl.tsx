import { useId, useLayoutEffect, useRef, useState } from "react";
import {
  DEFAULT_APPEARANCE, displayAppearance, readDisplayedAppearance, saveAppearance,
  type AppearanceAccent, type AppearanceSettings,
} from "./appearanceSettings";

const PRESETS = [
  { id: "default", label: "Buddy" },
  { id: "deep-teal", label: "Deep Teal" },
  { id: "wayfinder", label: "Wayfinder" },
] as const;

export function AppearanceControl({ proposedAccent, onApplied }: {
  proposedAccent?: AppearanceAccent;
  onApplied?: () => void;
} = {}) {
  const titleId = useId();
  const dialog = useRef<HTMLDialogElement>(null);
  const saved = useRef<AppearanceSettings>(DEFAULT_APPEARANCE);
  const [preview, setPreview] = useState<AppearanceSettings>(DEFAULT_APPEARANCE);

  useLayoutEffect(() => {
    const panel = dialog.current;
    return () => {
      if (panel?.open) displayAppearance(saved.current);
    };
  }, []);

  function open() {
    saved.current = readDisplayedAppearance();
    dialog.current?.showModal();
    select(proposedAccent === undefined ? saved.current : { ...saved.current, accent: proposedAccent });
  }

  function select(settings: AppearanceSettings) {
    setPreview(settings);
    displayAppearance(settings);
  }

  function apply() {
    saved.current = preview;
    saveAppearance(preview);
    dialog.current?.close();
    onApplied?.();
  }

  return <>
    <button className="app-nav-appearance" type="button" onClick={open}>{proposedAccent === undefined ? "Appearance" : "Preview accent"}</button>
    <dialog className="app-appearance" ref={dialog} aria-labelledby={titleId} onClose={() => displayAppearance(saved.current)}>
      <h2 id={titleId}>Appearance</h2>
      {proposedAccent === undefined ? <>
      <fieldset>
        <legend>Interface</legend>
        {PRESETS.map(({ id, label }) => <label key={id}>
          <input type="radio" name={titleId} checked={preview.preset === id} onChange={() => select({ ...preview, preset: id })} />
          {label}
        </label>)}
      </fieldset>
      <fieldset>
        <legend>Page style</legend>
        <label>
          <input type="radio" name={`${titleId}-page`} checked={preview.pageStyle === "original"}
            onChange={() => select({ ...preview, pageStyle: "original" })} />
          Original page styles
        </label>
        <label>
          <input type="radio" name={`${titleId}-page`} checked={preview.pageStyle === "dossier"}
            onChange={() => select({ ...preview, pageStyle: "dossier" })} />
          Dossier
        </label>
      </fieldset>
      <fieldset>
        <legend>Accent</legend>
        <label>
          <input type="radio" name={`${titleId}-accent`} checked={preview.accent === "preset"}
            onChange={() => select({ ...preview, accent: "preset" })} />
          Use theme accent
        </label>
        <label>
          <input type="radio" name={`${titleId}-accent`} checked={preview.accent === "sky"}
            onChange={() => select({ ...preview, accent: "sky" })} />
          Sky blue
        </label>
      </fieldset>
      </> : <p>Accent · {proposedAccent === "sky" ? "Sky blue" : "Theme default"}</p>}
      <div className="app-appearance__actions">
        {proposedAccent === undefined && <button type="button" onClick={() => select(DEFAULT_APPEARANCE)} disabled={preview.preset === "default" && preview.accent === "preset" && preview.pageStyle === "original"}>Reset</button>}
        <button type="button" onClick={() => dialog.current?.close()}>Cancel</button>
        <button type="button" onClick={apply}>Apply</button>
      </div>
    </dialog>
  </>;
}

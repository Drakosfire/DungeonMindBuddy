export type AppearancePreset = "default" | "deep-teal";
export type AppearanceAccent = "preset" | "sky";

export interface AppearanceSettings {
  preset: AppearancePreset;
  accent: AppearanceAccent;
}

export const DEFAULT_APPEARANCE: AppearanceSettings = { preset: "default", accent: "preset" };
const STORAGE_KEY = "buddy.appearance.settings";
const LEGACY_PRESET_KEY = "buddy.appearance.preset";

export function readDisplayedAppearance(): AppearanceSettings {
  const { buddyTheme, buddyAccent } = document.documentElement.dataset;
  return {
    preset: buddyTheme === "deep-teal" ? "deep-teal" : "default",
    accent: buddyAccent === "sky" ? "sky" : "preset",
  };
}

export function displayAppearance(settings: AppearanceSettings) {
  const root = document.documentElement;
  if (settings.preset === "default") delete root.dataset.buddyTheme;
  else root.dataset.buddyTheme = settings.preset;
  if (settings.accent === "preset") delete root.dataset.buddyAccent;
  else root.dataset.buddyAccent = settings.accent;
}

export function saveAppearance(settings: AppearanceSettings) {
  displayAppearance(settings);
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    localStorage.removeItem(LEGACY_PRESET_KEY);
  } catch {
    // The current tab can still use the chosen settings.
  }
}

/** Only a direct request about Buddy's appearance can offer this local action. */
export function appearanceAccentRequest(message: string): AppearanceAccent | null {
  const request = /^(?:please )?(?:set|change|switch|make) (?:the |my )?(?:buddy(?:['’]s)? |app )?accent (?:to )?(sky blue|the theme default|the default)[.!]?$/i.exec(message.trim());
  if (!request) return null;
  return request[1].toLowerCase() === "sky blue" ? "sky" : "preset";
}

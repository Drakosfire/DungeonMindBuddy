/**
 * Markdown theme registry and helpers for Command Board previews.
 */
(function (global) {
  const FALLBACK_THEME_ID = "command";

  const registry = {
    defaultThemeId: FALLBACK_THEME_ID,
    themes: {
      command: {
        label: "Command Board",
        className: "md-theme-command",
        variables: {
          "--md-bg": "var(--bg-card)",
          "--md-surface": "var(--bg-input)",
          "--md-fg": "var(--fg)",
          "--md-muted": "var(--fg-mute)",
          "--md-border": "var(--border)",
          "--md-accent": "var(--accent)",
          "--md-heading": "var(--fg)",
        },
      },

      statblock: {
        label: "DungeonMind Statblock",
        className: "md-theme-statblock",
        variables: {
          "--md-bg": "#f7ebd7",
          "--md-surface": "rgba(255, 249, 237, 0.85)",
          "--md-fg": "#2b1d0f",
          "--md-muted": "rgba(43, 29, 15, 0.72)",
          "--md-border": "#c0ad6a",
          "--md-accent": "#a11d18",
          "--md-heading": "#58180d",
        },
      },

      plain: {
        label: "Plain Reference",
        className: "md-theme-plain",
        variables: {},
      },
    },
  };

  function getRegistry() {
    return global.MirewardMarkdownThemes || registry;
  }

  function getMarkdownTheme(themeId) {
    const activeRegistry = getRegistry();
    const themes = activeRegistry.themes || {};
    const requested = typeof themeId === "string" ? themeId : "";
    const defaultId =
      typeof activeRegistry.defaultThemeId === "string"
        ? activeRegistry.defaultThemeId
        : FALLBACK_THEME_ID;
    const resolvedId = themes[requested]
      ? requested
      : themes[defaultId]
        ? defaultId
        : FALLBACK_THEME_ID;

    return {
      id: resolvedId,
      theme: themes[resolvedId] || registry.themes[FALLBACK_THEME_ID],
    };
  }

  function clearMarkdownTheme(el) {
    if (!el) return;

    Array.from(el.classList || []).forEach(function (className) {
      if (className.indexOf("md-theme-") === 0) {
        el.classList.remove(className);
      }
    });

    if (el.style) {
      Array.from(el.style).forEach(function (propertyName) {
        if (propertyName.indexOf("--md-") === 0) {
          el.style.removeProperty(propertyName);
        }
      });
    }

    if (el.removeAttribute) {
      el.removeAttribute("data-md-theme");
    }
  }

  function applyMarkdownTheme(el, themeId) {
    if (!el) return undefined;

    const resolved = getMarkdownTheme(themeId);
    const theme = resolved.theme || {};
    clearMarkdownTheme(el);

    if (theme.className && el.classList) {
      el.classList.add(theme.className);
    }

    if (el.setAttribute) {
      el.setAttribute("data-md-theme", resolved.id);
    }

    if (el.style) {
      Object.entries(theme.variables || {}).forEach(function (entry) {
        el.style.setProperty(entry[0], entry[1]);
      });
    }

    return resolved.id;
  }

  global.MirewardMarkdownThemes = registry;
  global.MirewardMarkdownThemeTools = {
    getMarkdownTheme: getMarkdownTheme,
    clearMarkdownTheme: clearMarkdownTheme,
    applyMarkdownTheme: applyMarkdownTheme,
  };
})(window);

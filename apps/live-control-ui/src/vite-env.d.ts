/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_LIVE_API_BASE_URL?: string;
  readonly VITE_LIVE_PLANNING_MANIFEST_PATH?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_LIVE_API_BASE_URL?: string;
  readonly VITE_LIVE_PLANNING_MANIFEST_PATH?: string;
  /** OPT-BENCH02: enable client surface-latency instrumentation at build/dev time. */
  readonly VITE_DMB_BENCH_SURFACE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

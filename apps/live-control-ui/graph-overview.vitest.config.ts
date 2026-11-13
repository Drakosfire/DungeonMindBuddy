import { defineConfig, mergeConfig } from "vitest/config";
import appConfig from "./vite.config";

export default mergeConfig(appConfig, defineConfig({
  test: {
    include: ["src/localWorld/worldGraphCanvas/fullGraphOverview.benchmark.tsx"],
  },
}));

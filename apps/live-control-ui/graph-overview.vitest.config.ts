import { defineConfig, mergeConfig } from "vitest/config";
import appConfig from "./vite.config";

export default mergeConfig(appConfig, defineConfig({
  test: {
    environment: "jsdom",
    include: ["src/localWorld/worldGraphCanvas/fullGraphOverview.benchmark.tsx"],
  },
}));

import {fileURLToPath} from 'node:url';
import {defineConfig} from 'vitest/config';
export default defineConfig({
  esbuild:{jsx:'automatic'},
  test:{root:fileURLToPath(new URL('../..',import.meta.url)),environment:'jsdom',
    setupFiles:['apps/live-control-ui/src/test/setup.ts'],globals:true,maxWorkers:1,
    include:['evals/inline_prose_targeting/*.test.{ts,tsx}',
      'apps/live-control-ui/src/buildSurface/buildComposeBridge.test.ts',
      'apps/live-control-ui/src/buildSurface/BuildPageProposal.test.tsx',
      'apps/live-control-ui/src/documentEditing/markdownInsertion.test.ts']},
});

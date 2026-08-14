import { defineConfig, mergeConfig } from 'vitest/config';
import viteConfig from './vite.config';

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      exclude: ['e2e/**', 'node_modules/**'],
      environment: 'jsdom',
      setupFiles: './src/test/setup.ts',
      css: true,
    },
  }),
);

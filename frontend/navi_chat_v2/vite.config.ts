import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react-swc';
import { resolve } from 'path';
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  const udfVars: Record<string, string> = {};
  for (const key of ['VITE_UDF_PUBLIC_URL', 'VITE_UDF_CLIENT_ID', 'VITE_UDF_TENANT_ID']) {
    const val = env[key];
    if (val) {
      udfVars[`import.meta.env.${key}`] = JSON.stringify(val);
    }
  }

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': resolve(import.meta.dirname, 'src'),
      },
    },
    define: udfVars,
    build: {
      target: 'es2022',
    },
    esbuild: {
      target: 'es2022',
    },
    optimizeDeps: {
      exclude: ['maplibre-gl'],
      esbuildOptions: {
        target: 'es2022',
      },
    },
  };
});
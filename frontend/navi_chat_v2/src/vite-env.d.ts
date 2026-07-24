/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_RAYFIN_API_URL: string;
  readonly VITE_RAYFIN_PUBLISHABLE_KEY: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
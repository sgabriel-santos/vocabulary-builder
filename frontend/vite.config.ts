import { fileURLToPath, URL } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";
import { VitePWA } from "vite-plugin-pwa";

// O .env fica na raiz do repositório (compartilhado com o backend).
const envDir = fileURLToPath(new URL("..", import.meta.url));

export default defineConfig(({ mode }) => {
  // Prefixo "" carrega todas as variáveis, mas só para este arquivo de config;
  // nada disso é exposto ao bundle do cliente.
  const env = loadEnv(mode, envDir, "");
  const apiPort = env.API_PORT ?? "8000";

  return {
    plugins: [
      // O plugin do router precisa vir antes do react().
      tanstackRouter({ target: "react", autoCodeSplitting: true }),
      react(),
      tailwindcss(),
      VitePWA({
        registerType: "prompt",
        manifest: {
          name: "Vocabulary Builder",
          short_name: "Vocab",
          lang: "pt-BR",
          display: "standalone",
          start_url: "/",
          theme_color: "#171717",
          background_color: "#ffffff",
          icons: [
            { src: "pwa-192x192.png", sizes: "192x192", type: "image/png" },
            { src: "pwa-512x512.png", sizes: "512x512", type: "image/png" },
            {
              src: "maskable-icon-512x512.png",
              sizes: "512x512",
              type: "image/png",
              purpose: "maskable",
            },
          ],
        },
        workbox: {
          globPatterns: ["**/*.{js,css,html,svg,png,ico,woff2,webmanifest}"],
          // A API nunca é servida pelo service worker (offline fora do escopo).
          navigateFallbackDenylist: [/^\/api\//],
        },
      }),
    ],
    resolve: {
      alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
    },
    server: {
      port: 5173,
      strictPort: true,
      // Mesma origem em dev: o navegador fala só com o Vite, que repassa /api.
      proxy: { "/api": `http://localhost:${apiPort}` },
    },
  };
});

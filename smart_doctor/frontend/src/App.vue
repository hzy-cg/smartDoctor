<template>
  <n-config-provider :theme-overrides="themeOverrides">
    <n-message-provider>
      <div class="app-shell">
        <AppHeader v-if="$route.path !== '/login'" />
        <main class="app-main" :class="{ 'no-header': $route.path === '/login' }">
          <router-view />
        </main>
      </div>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import type { GlobalThemeOverrides } from "naive-ui";
import { NConfigProvider, NMessageProvider } from "naive-ui";
import AppHeader from "@/components/common/AppHeader.vue";

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: "#0D9488",
    primaryColorHover: "#0F766E",
    primaryColorPressed: "#115E59",
    primaryColorSuppl: "#14B8A6",
    borderRadius: "10px",
    borderRadiusSmall: "8px",
    fontFamily: "'Noto Sans SC', 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif",
    fontSize: "14px",
  },
  Button: {
    borderRadiusMedium: "10px",
    heightMedium: "40px",
  },
  Input: {
    borderRadius: "10px",
  },
  Card: {
    borderRadius: "14px",
  },
};
</script>

<style>
:root {
  --c-primary: #0d9488;
  --c-primary-light: #14b8a6;
  --c-primary-dark: #0f766e;
  --c-primary-50: #f0fdfa;
  --c-primary-100: #ccfbf1;
  --c-primary-200: #99f6e4;
  --c-neutral-50: #f8fafc;
  --c-neutral-100: #f1f5f9;
  --c-neutral-200: #e2e8f0;
  --c-neutral-300: #cbd5e1;
  --c-neutral-400: #94a3b8;
  --c-neutral-500: #64748b;
  --c-neutral-600: #475569;
  --c-neutral-700: #334155;
  --c-neutral-800: #1e293b;
  --c-neutral-900: #0f172a;
  --c-amber: #f59e0b;
  --c-rose: #f43f5e;
  --c-rose-50: #fff1f2;
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
  --shadow-lg: 0 8px 30px rgba(0,0,0,0.12);
  --transition: 0.2s ease;
}

* { margin: 0; padding: 0; box-sizing: border-box; }
html, body, #app { height: 100%; width: 100%; overflow: hidden; }

body {
  font-family: 'Noto Sans SC', 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
  -webkit-font-smoothing: antialiased;
  background: var(--c-neutral-50);
  color: var(--c-neutral-800);
}

.app-shell { display: flex; flex-direction: column; height: 100%; }
.app-main { flex: 1; min-height: 0; overflow: hidden; display: flex; flex-direction: column; }
.app-main.no-header { height: 100%; }

::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--c-neutral-300); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--c-neutral-400); }

@keyframes fadeUp { from { opacity:0; transform:translateY(16px); } to { opacity:1; transform:translateY(0); } }
@keyframes fadeIn { from { opacity:0; } to { opacity:1; } }
@keyframes pulse3 { 0%,80%,100%{opacity:.3;transform:scale(.8)} 40%{opacity:1;transform:scale(1)} }
</style>

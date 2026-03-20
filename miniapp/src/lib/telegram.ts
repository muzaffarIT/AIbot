"use client";

export type TelegramUser = {
  id?: number;
  username?: string;
  first_name?: string;
  last_name?: string;
  language_code?: string;
};

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        ready: () => void;
        expand: () => void;
        sendData?: (data: string) => void;
        initDataUnsafe?: {
          user?: TelegramUser;
        };
      };
    };
  }
}

export function initTelegramWebApp() {
  if (typeof window === "undefined") return;

  const webApp = window.Telegram?.WebApp;
  if (!webApp) return;

  webApp.ready();
  webApp.expand();
}

export function getTelegramUser() {
  if (typeof window === "undefined") return null;
  return window.Telegram?.WebApp?.initDataUnsafe?.user ?? null;
}

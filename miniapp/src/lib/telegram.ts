"use client";

export type TelegramUser = {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  photo_url?: string;
};

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        ready: () => void;
        expand: () => void;
        close: () => void;
        sendData?: (data: string) => void;
        initData?: string;
        initDataUnsafe?: {
          user?: TelegramUser;
          start_param?: string;
        };
        colorScheme?: "light" | "dark";
        HapticFeedback?: {
          impactOccurred: (style: "light" | "medium" | "heavy" | "rigid" | "soft") => void;
          notificationOccurred: (type: "error" | "success" | "warning") => void;
          selectionChanged: () => void;
        };
      };
    };
  }
}

export function getTelegramWebApp() {
  if (typeof window === "undefined") return null;
  return window.Telegram?.WebApp ?? null;
}

export function getTelegramUser(): TelegramUser | null {
  const tg = getTelegramWebApp();
  return tg?.initDataUnsafe?.user ?? null;
}

export function getInitData(): string {
  const tg = getTelegramWebApp();
  return tg?.initData ?? "";
}

export function initTelegram(): boolean {
  const tg = getTelegramWebApp();
  if (!tg) return false;
  tg.ready();
  tg.expand();
  return true;
}

// Legacy alias
export function initTelegramWebApp() {
  initTelegram();
}

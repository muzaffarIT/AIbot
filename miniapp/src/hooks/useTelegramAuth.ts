"use client";

import { useEffect, useState, useCallback } from "react";
import { api, type BackendUser } from "@/lib/api";

export interface TgUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
}

/** Парсим user из initData напрямую (fallback если initDataUnsafe пуст) */
function parseUserFromInitData(initData: string): TgUser | null {
  try {
    const params = new URLSearchParams(initData);
    const userJson = params.get("user");
    if (!userJson) return null;
    const u = JSON.parse(decodeURIComponent(userJson));
    if (u?.id) return u as TgUser;
  } catch {}
  return null;
}

export function useTelegramAuth() {
  const [tgUser, setTgUser] = useState<TgUser | null>(null);
  const [userData, setUserData] = useState<BackendUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const syncWithBackend = async (user: TgUser) => {
      try {
        const synced = await api.syncUser({
          telegram_id: user.id,
          username: user.username,
          first_name: user.first_name,
          last_name: user.last_name,
          language_code: user.language_code,
        });
        if (!cancelled) {
          setUserData(synced);
          setError(null);
        }
      } catch (err: any) {
        if (!cancelled) {
          try {
            const cached = sessionStorage.getItem("harf_user");
            if (cached) {
              setUserData(JSON.parse(cached) as BackendUser);
              setError(null);
              return;
            }
          } catch {}
          setError(err?.message ?? "Ошибка синхронизации");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    const getUser = (tg: any): TgUser | null => {
      // Способ 1: initDataUnsafe (стандартный)
      const u = tg?.initDataUnsafe?.user;
      if (u?.id) return u as TgUser;

      // Способ 2: парсим initData напрямую (fallback для Desktop)
      if (tg?.initData) return parseUserFromInitData(tg.initData);

      return null;
    };

    // Polling: ждём пока user станет доступен (до 3 секунд)
    let attempts = 0;
    const MAX_ATTEMPTS = 30;

    const check = (): boolean => {
      const tg = (window as any).Telegram?.WebApp;

      const user = getUser(tg);
      if (user) {
        tg.ready();
        tg.expand();
        if (!cancelled) setTgUser(user);
        void syncWithBackend(user);
        return true;
      }

      attempts++;
      if (attempts >= MAX_ATTEMPTS) {
        if (!cancelled) {
          const tgExists = !!(window as any).Telegram?.WebApp;
          setError(tgExists ? "Нет данных пользователя" : "Откройте через Telegram");
          setLoading(false);
        }
        return true;
      }
      return false;
    };

    if (check()) return;

    const interval = setInterval(() => {
      if (check()) clearInterval(interval);
    }, 100);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    if (userData) {
      try { sessionStorage.setItem("harf_user", JSON.stringify(userData)); } catch {}
    }
  }, [userData]);

  const refresh = useCallback(async () => {
    if (!tgUser) return;
    try {
      const synced = await api.syncUser({
        telegram_id: tgUser.id,
        username: tgUser.username,
        first_name: tgUser.first_name,
        last_name: tgUser.last_name,
        language_code: tgUser.language_code,
      });
      setUserData(synced);
    } catch {}
  }, [tgUser]);

  return { tgUser, userData, loading, error, refresh };
}

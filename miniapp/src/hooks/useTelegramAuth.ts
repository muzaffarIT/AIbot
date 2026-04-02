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
          // Fallback: попробуем загрузить из кэша
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

    // Polling: ждём пока initDataUnsafe.user станет доступен
    // Telegram WebApp может быть загружен, но user ещё не заполнен
    let attempts = 0;
    const MAX_ATTEMPTS = 30; // 3 секунды (30 × 100ms)

    const check = () => {
      const tg = (window as any).Telegram?.WebApp;

      if (tg?.initDataUnsafe?.user?.id) {
        // Telegram готов, user доступен
        tg.ready();
        tg.expand();
        const user = tg.initDataUnsafe.user as TgUser;
        if (!cancelled) setTgUser(user);
        void syncWithBackend(user);
        return true;
      }

      attempts++;

      if (attempts >= MAX_ATTEMPTS) {
        // Timeout: Telegram не предоставил данные
        if (!cancelled) {
          const tgExists = !!(window as any).Telegram?.WebApp;
          setError(tgExists ? "Нет данных пользователя" : "Откройте через Telegram");
          setLoading(false);
        }
        return true; // stop polling
      }

      return false;
    };

    // Сразу пробуем
    if (check()) return;

    // Иначе polling каждые 100ms
    const interval = setInterval(() => {
      if (check()) clearInterval(interval);
    }, 100);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // Кэшируем userData в sessionStorage при изменении
  useEffect(() => {
    if (userData) {
      try {
        sessionStorage.setItem("harf_user", JSON.stringify(userData));
      } catch {}
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

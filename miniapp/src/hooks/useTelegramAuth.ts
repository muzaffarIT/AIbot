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

    const init = async () => {
      try {
        const tg = (window as any).Telegram?.WebApp;
        if (!tg) {
          if (!cancelled) {
            setError("Откройте через Telegram");
            setLoading(false);
          }
          return;
        }

        // Инициализируем WebApp
        tg.ready();
        tg.expand();

        const user = tg.initDataUnsafe?.user as TgUser | undefined;
        if (!user?.id) {
          if (!cancelled) {
            setError("Нет данных пользователя");
            setLoading(false);
          }
          return;
        }

        if (!cancelled) setTgUser(user);

        // Синхронизируем с backend (initData уже доступен, auth пройдёт)
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
          // Пробуем загрузить из кэша
          try {
            const cached = sessionStorage.getItem("harf_user");
            if (cached) {
              const parsed = JSON.parse(cached) as BackendUser;
              setUserData(parsed);
              setError(null);
              return;
            }
          } catch {}
          setError(err?.message ?? "Ошибка загрузки данных");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    // Если Telegram WebApp уже загружен — запускаем сразу, иначе ждём 500ms
    if ((window as any).Telegram?.WebApp) {
      void init();
    } else {
      const timer = setTimeout(() => { void init(); }, 500);
      return () => {
        cancelled = true;
        clearTimeout(timer);
      };
    }

    return () => {
      cancelled = true;
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

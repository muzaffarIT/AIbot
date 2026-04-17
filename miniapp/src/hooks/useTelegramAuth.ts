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

/** Парсим user из initData (fallback для Telegram Desktop) */
function parseUserFromInitData(initData: string): TgUser | null {
  try {
    const params = new URLSearchParams(initData);
    const raw = params.get("user");
    if (!raw) return null;
    // URLSearchParams.get() уже декодирует %, так что просто парсим
    const u = JSON.parse(raw);
    if (u?.id) return u as TgUser;
  } catch {}
  return null;
}

function getUser(tg: any): TgUser | null {
  if (!tg) return null;
  // Метод 1: initDataUnsafe (стандартный)
  const u = tg.initDataUnsafe?.user;
  if (u?.id) return u as TgUser;
  // Метод 2: парсим initData напрямую
  if (tg.initData) return parseUserFromInitData(tg.initData);
  return null;
}

function loadCachedUser(): BackendUser | null {
  try {
    const s = localStorage.getItem("harf_user");
    return s ? (JSON.parse(s) as BackendUser) : null;
  } catch {
    return null;
  }
}

export function useTelegramAuth() {
  // Сразу грузим из кэша — не показываем лоадер при повторных заходах
  const [tgUser, setTgUser] = useState<TgUser | null>(null);
  const [userData, setUserData] = useState<BackendUser | null>(loadCachedUser);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    // Если уже есть кэш — снимаем loading сразу, но всё равно пробуем обновить
    if (userData) setLoading(false);

    const syncWithBackend = async (user: TgUser) => {
      try {
        const synced = await api.syncUser({
          telegram_id: user.id,
          username: user.username,
          first_name: user.first_name,
          last_name: user.last_name,
          // Don't send Telegram app language — it would overwrite user's bot-chosen language in DB
          language_code: null,
        });
        if (!cancelled) {
          setUserData(synced);
          setError(null);
        }
      } catch {
        // syncUser requires TMA auth — if initData not available, fall back to public profile endpoint
        try {
          const profile = await api.getProfile(user.id);
          if (!cancelled) {
            setUserData(profile);
            setError(null);
          }
        } catch (fallbackErr: any) {
          if (!cancelled && !loadCachedUser()) {
            setError(fallbackErr?.message ?? "Ошибка загрузки профиля");
          }
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    // Polling: ждём initData до 5 секунд (50 × 100ms)
    let attempts = 0;
    const MAX_ATTEMPTS = 50;

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
          // Не показываем жёсткую ошибку если есть кэш
          if (!loadCachedUser()) {
            const tgExists = !!(window as any).Telegram?.WebApp;
            setError(tgExists ? "Нет данных пользователя" : "Откройте через Telegram");
          }
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
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (userData) {
      try {
        localStorage.setItem("harf_user", JSON.stringify(userData));
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
        language_code: null,
      });
      setUserData(synced);
    } catch {
      // Fallback to public profile endpoint when TMA auth fails
      try {
        const profile = await api.getProfile(tgUser.id);
        setUserData(profile);
      } catch {}
    }
  }, [tgUser]);

  // Re-sync balance when user returns to the tab (switches pages in Telegram)
  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState === "visible") {
        void refresh();
      }
    };
    document.addEventListener("visibilitychange", handleVisibility);
    return () => document.removeEventListener("visibilitychange", handleVisibility);
  }, [refresh]);

  return { tgUser, userData, loading, error, refresh };
}

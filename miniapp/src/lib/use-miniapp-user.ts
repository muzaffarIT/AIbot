"use client";

import { useEffect, useState } from "react";
import { getUser, syncUser as apiSyncUser, updateLanguage, type BackendUser } from "@/lib/api";
import { useTelegramUser } from "@/hooks/useTelegramUser";
import {
  normalizeLanguage,
  type MiniAppLanguage,
} from "@/lib/miniapp-i18n";

export function useMiniAppUser() {
  const { tgUser, ready } = useTelegramUser();
  const [backendUser, setBackendUser] = useState<BackendUser | null>(null);
  const [language, setLanguage] = useState<MiniAppLanguage>("ru");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    if (!ready) return;
    if (!tgUser?.id) {
      setLoading(false);
      return;
    }

    async function sync() {
      console.log('[SYNC] Starting sync for user:', tgUser.id);
      setLoading(true);
      try {
        const beUser = await apiSyncUser({
          telegram_id: tgUser.id,
          username: tgUser.username,
          first_name: tgUser.first_name,
          last_name: tgUser.last_name,
          language_code: tgUser.language_code,
        });
        console.log('[SYNC] Success:', beUser.id);
        setBackendUser(beUser);
        setLanguage(normalizeLanguage(beUser.language_code));
        localStorage.setItem("miniapp_language", normalizeLanguage(beUser.language_code));
        try {
          sessionStorage.setItem('harf_user', JSON.stringify(beUser));
        } catch {}
        setError("");
      } catch (e: any) {
        console.error('[SYNC] Failed:', e);
        const cached = sessionStorage.getItem('harf_user');
        if (cached) {
          try {
            const beUser = JSON.parse(cached);
            console.log('[SYNC] Loaded from cache after failure');
            setBackendUser(beUser);
            setLanguage(normalizeLanguage(beUser.language_code));
          } catch {}
        } else {
          setError("sync_failed");
        }
      } finally {
        setLoading(false);
      }
    }

    sync();
  }, [ready, tgUser, retryCount]);

  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.lang = language;
    }
  }, [language]);

  const changeLanguage = async (newLang: string) => {
    setLanguage(newLang as MiniAppLanguage);
    localStorage.setItem("miniapp_language", newLang);
    if (backendUser) {
      try {
        await updateLanguage(backendUser.telegram_user_id, newLang);
      } catch (e) {
        console.error("Failed to update language on backend", e);
      }
    }
  };

  const syncUser = () => {
    setRetryCount(c => c + 1);
  };

  return {
    telegramUser: tgUser,
    backendUser,
    language,
    loading,
    error,
    changeLanguage,
    syncUser,
  };
}

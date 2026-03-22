"use client";

import { useEffect, useState } from "react";
import { getUser, syncUser as apiSyncUser, updateLanguage, type BackendUser } from "@/lib/api";
import {
  getTelegramUser,
  initTelegramWebApp,
  type TelegramUser,
} from "@/lib/telegram";
import {
  normalizeLanguage,
  type MiniAppLanguage,
} from "@/lib/miniapp-i18n";

export function useMiniAppUser() {
  const [telegramUser, setTelegramUser] = useState<TelegramUser | null>(null);
  const [backendUser, setBackendUser] = useState<BackendUser | null>(null);
  const [language, setLanguage] = useState<MiniAppLanguage>("ru");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retryCount, setRetryCount] = useState(0);
  useEffect(() => {
    initTelegramWebApp();

    let attempts = 0;

    async function sync(user: TelegramUser) {
      setTelegramUser(user);
      setLanguage(normalizeLanguage(user?.language_code));

      try {
        let beUser: BackendUser;
        try {
          beUser = await getUser(user.id!);
        } catch (e: any) {
          // If 404 or other error, fallback to sync
          beUser = await apiSyncUser({
            telegram_id: user.id!,
            username: user.username,
            first_name: user.first_name,
            last_name: user.last_name,
            language_code: user.language_code,
          });
        }
        setBackendUser(beUser);
        setLanguage(normalizeLanguage(beUser.language_code));
        localStorage.setItem("miniapp_language", normalizeLanguage(beUser.language_code));
        setError(""); // Clear any previous error
      } catch (syncError) {
        // Silently log errors and don't spam user UI
        console.error('Cabinet load error:', syncError);
        setError("sync_failed");
      } finally {
        setLoading(false);
      }
    }

    function checkUser() {
      const user = getTelegramUser();
      if (user?.id) {
        void sync(user);
      } else if (attempts < 20) {
        attempts++;
        setTimeout(checkUser, 100);
      } else {
        setLoading(false);
      }
    }

    checkUser();
  }, [retryCount]);

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
    setLoading(true);
    setRetryCount(c => c + 1);
  };

  return {
    telegramUser,
    backendUser,
    language,
    loading,
    error,
    changeLanguage,
    syncUser,
  };
}

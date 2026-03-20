"use client";

import { useEffect, useState } from "react";
import { ensureUser, type BackendUser } from "@/lib/api";
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

  useEffect(() => {
    initTelegramWebApp();

    let attempts = 0;

    async function sync(user: TelegramUser) {
      setTelegramUser(user);
      setLanguage(normalizeLanguage(user?.language_code));

      try {
        const ensuredUser = await ensureUser({
          telegram_user_id: user.id!,
          username: user.username,
          first_name: user.first_name,
          last_name: user.last_name,
        });
        setBackendUser(ensuredUser);
        setLanguage(normalizeLanguage(ensuredUser.language_code));
      } catch (syncError) {
        if (syncError instanceof Error && syncError.message) {
          setError(syncError.message);
        } else {
          setError("sync_failed");
        }
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
  }, []);

  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.lang = language;
    }
  }, [language]);

  return {
    telegramUser,
    backendUser,
    language,
    loading,
    error,
  };
}

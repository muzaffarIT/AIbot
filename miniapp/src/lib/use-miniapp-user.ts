"use client";

import { useState, useEffect } from "react";
import { useTelegramAuth } from "@/hooks/useTelegramAuth";
import { updateLanguage, type BackendUser } from "@/lib/api";
import { normalizeLanguage, type MiniAppLanguage } from "@/lib/miniapp-i18n";

export function useMiniAppUser() {
  const { tgUser, userData, loading, error, refresh } = useTelegramAuth();
  const [language, setLanguage] = useState<MiniAppLanguage>("ru");

  // Синхронизируем язык из backend
  useEffect(() => {
    if (userData?.language_code) {
      const lang = normalizeLanguage(userData.language_code);
      setLanguage(lang);
      try { localStorage.setItem("miniapp_language", lang); } catch {}
    }
  }, [userData?.language_code]);

  // Обновляем lang атрибут html
  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.lang = language;
    }
  }, [language]);

  const changeLanguage = async (newLang: string) => {
    setLanguage(newLang as MiniAppLanguage);
    try { localStorage.setItem("miniapp_language", newLang); } catch {}
    if (userData?.telegram_user_id) {
      try {
        await updateLanguage(userData.telegram_user_id, newLang);
      } catch {}
    }
  };

  return {
    telegramUser: tgUser,
    backendUser: userData as BackendUser | null,
    language,
    loading,
    error: error ?? "",
    changeLanguage,
    syncUser: refresh,
  };
}

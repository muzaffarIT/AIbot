"use client";

import { useState, useEffect } from "react";
import { useTelegramAuth } from "@/hooks/useTelegramAuth";
import { updateLanguage, type BackendUser } from "@/lib/api";
import { normalizeLanguage, type MiniAppLanguage } from "@/lib/miniapp-i18n";

function loadCachedLanguage(): MiniAppLanguage {
  try {
    // Prioritize the cached backend user's language_code (set by bot)
    // over the standalone miniapp_language key (which may be stale)
    const raw = localStorage.getItem("harf_user");
    if (raw) {
      const u = JSON.parse(raw);
      if (u?.language_code === "uz" || u?.language_code === "ru") {
        return u.language_code as MiniAppLanguage;
      }
    }
    // Fallback: standalone key
    const l = localStorage.getItem("miniapp_language");
    if (l === "uz" || l === "ru") return l;
  } catch {}
  return "ru";
}

export function useMiniAppUser() {
  const { tgUser, userData, loading, error, refresh } = useTelegramAuth();
  const [language, setLanguage] = useState<MiniAppLanguage>(loadCachedLanguage);

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
    const lang = newLang as MiniAppLanguage;
    setLanguage(lang);
    // Persist to both keys so loadCachedLanguage reads the new value on next open
    try {
      localStorage.setItem("miniapp_language", lang);
      // Also update harf_user.language_code in cache so it wins on next load
      const raw = localStorage.getItem("harf_user");
      if (raw) {
        const u = JSON.parse(raw);
        u.language_code = lang;
        localStorage.setItem("harf_user", JSON.stringify(u));
      }
    } catch {}
    if (userData?.telegram_user_id) {
      try {
        await updateLanguage(userData.telegram_user_id, lang);
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

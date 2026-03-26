"use client";

import { useEffect } from "react";

export function TelegramInit() {
  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (!tg) return;

    tg.ready();
    tg.expand();

    const tgUser = tg.initDataUnsafe?.user;
    if (!tgUser) {
      console.warn("No Telegram user data available");
      return;
    }

    // Sync user with backend
    fetch("/api/users/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        telegram_id: tgUser.id,
        username: tgUser.username || "",
        first_name: tgUser.first_name || "",
        last_name: tgUser.last_name || "",
        language_code: tgUser.language_code || "ru",
      }),
    })
      .then((r) => r.json())
      .then((userData) => {
        if (userData && userData.telegram_id) {
          // Cache user data for offline/slow network fallback
          try {
            localStorage.setItem("batir_user", JSON.stringify(userData));
          } catch {
            // ignore if localStorage unavailable
          }
        }
      })
      .catch((err) => console.error("Sync failed:", err));
  }, []);

  return null;
}

"use client";

import { useEffect } from "react";

export function TelegramInit() {
  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (!tg) return;

    tg.ready();
    tg.expand();

    const user = tg.initDataUnsafe?.user;
    if (!user) return;

    // Синхронизируем пользователя с backend
    fetch('/api/users/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        telegram_id: user.id,
        username: user.username || '',
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        language_code: user.language_code || 'ru'
      })
    })
    .catch(err => {
      console.error('Sync failed:', err);
    });
  }, []);

  return null;
}

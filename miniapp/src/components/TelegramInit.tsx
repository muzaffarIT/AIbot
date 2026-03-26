"use client";

import { useEffect } from "react";

export function TelegramInit() {
  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (!tg) return;

    tg.ready();
    tg.expand();

    const tgUser = tg.initDataUnsafe?.user;
    if (!tgUser) return;

    // mock setUser so it complies
    const setUser = (data: any) => localStorage.setItem('batir_user', JSON.stringify(data));

    fetch('/api/users/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        telegram_id: tgUser.id,
        username: tgUser.username || '',
        first_name: tgUser.first_name || '',
        last_name: tgUser.last_name || '',
        language_code: tgUser.language_code || 'ru'
      })
    })
    .then(r => r.json())
    .then(data => { if (data?.telegram_id) setUser(data) })
    .catch(err => console.error('Sync:', err))
  }, []);

  return null;
}

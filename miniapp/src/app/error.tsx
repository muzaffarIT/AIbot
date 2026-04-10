"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[HARF AI] Unhandled error:", error);
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-[#0f0f0f] p-6 text-center text-white">
      <div className="text-5xl">⚠️</div>
      <h1 className="text-xl font-bold">Что-то пошло не так</h1>
      <p className="text-sm text-gray-400">
        Произошла ошибка при загрузке страницы.
        <br />
        Попробуй ещё раз или перезапусти приложение.
      </p>
      <button
        onClick={reset}
        className="rounded-xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white hover:bg-blue-700 active:scale-95 transition-transform"
      >
        🔄 Попробовать снова
      </button>
    </div>
  );
}

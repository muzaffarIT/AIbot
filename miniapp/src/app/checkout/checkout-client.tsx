"use client";

import Link from "next/link";
import { useState } from "react";
import { useMiniAppUser } from "@/lib/use-miniapp-user";

type CheckoutClientProps = {
  planName?: string;
  amount?: string;
  currency?: string;
  credits?: string;
  orderId?: string;
  orderNumber?: string;
  paymentId?: string;
  cardNumber?: string;
  cardOwner?: string;
  visaCardNumber?: string;
  visaCardOwner?: string;
  alreadyPending?: string;
};

function fmt(n: number) {
  return n.toLocaleString("ru-RU");
}

export default function CheckoutClient({
  planName,
  amount,
  currency,
  credits,
  orderId,
  orderNumber,
  paymentId,
  cardNumber,
  cardOwner,
  visaCardNumber,
  visaCardOwner,
  alreadyPending,
}: CheckoutClientProps) {
  const { language } = useMiniAppUser();
  const [notified, setNotified] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const parsedAmount = Number(amount || "0");
  const parsedPaymentId = Number(paymentId || "0");
  const isRu = language !== "uz";

  async function handlePaid() {
    if (!parsedPaymentId) return;
    try {
      setLoading(true);
      setError("");
      const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL?.trim() ?? "";
      let initData = "";
      if (typeof window !== "undefined") {
        initData = (window as any).Telegram?.WebApp?.initData ?? "";
      }
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (initData) headers["Authorization"] = `tma ${initData}`;
      const res = await fetch(`${BACKEND_URL}/api/payments/${parsedPaymentId}/notify-paid`, {
        method: "POST",
        headers,
        cache: "no-store",
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error((data as any)?.detail || "Ошибка");
      }
      setNotified(true);
    } catch (e: any) {
      setError(e?.message ?? (isRu ? "Ошибка. Попробуйте снова." : "Xatolik. Qayta urinib ko'ring."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen px-5 pt-6 pb-24 overflow-x-hidden">
      <div className="max-w-md mx-auto space-y-5">

        {/* Header */}
        <div className="flex items-center gap-3">
          <Link
            href="/plans"
            className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-colors"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-white">
              <path d="M19 12H5M12 19l-7-7 7-7" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </Link>
          <h1 className="text-2xl font-bold text-white">
            {isRu ? "Оплата" : "To'lov"}
          </h1>
        </div>

        {/* Plan summary */}
        <div className="glass-card p-5 space-y-3">
          <p className="text-xs text-white/40 uppercase tracking-wider font-bold">
            {isRu ? "Ваш заказ" : "Buyurtmangiz"}
          </p>
          <div className="flex justify-between items-center">
            <span className="text-white font-semibold">{planName || (isRu ? "Тариф" : "Tarif")}</span>
            <span className="text-brand-cyan font-bold">{fmt(parsedAmount)} {isRu ? "сум" : "so'm"}</span>
          </div>
          <div className="flex justify-between items-center text-sm text-white/60">
            <span>{isRu ? "Кредиты" : "Kreditlar"}</span>
            <span className="text-white">⚡ {credits || "0"}</span>
          </div>
          {orderNumber && (
            <div className="flex justify-between items-center text-sm text-white/40">
              <span>{isRu ? "Заказ" : "Buyurtma"}</span>
              <span className="font-mono text-xs">{orderNumber}</span>
            </div>
          )}
        </div>

        {alreadyPending === "1" && (
          <div className="p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/20 text-sm text-yellow-300">
            {isRu
              ? "⚠️ У вас уже есть активная заявка на оплату. Оплатите по реквизитам ниже и нажмите «Я оплатил»."
              : "⚠️ Sizda allaqachon faol to'lov arizasi mavjud. Quyidagi ma'lumotlar bo'yicha to'lang."}
          </div>
        )}

        {/* Card details */}
        {(cardNumber || visaCardNumber) ? (
          <div className="glass-card p-5 space-y-4">
            <p className="text-xs text-white/40 uppercase tracking-wider font-bold">
              {isRu ? "Реквизиты для перевода" : "To'lov ma'lumotlari"}
            </p>

            {cardNumber && (
              <div className="space-y-1">
                <p className="text-xs text-white/40">Humo / Uzcard</p>
                <button
                  onClick={() => navigator.clipboard?.writeText(cardNumber)}
                  className="w-full text-left font-mono text-lg font-bold text-white bg-white/5 rounded-xl px-4 py-3 hover:bg-white/10 transition-colors"
                >
                  {cardNumber}
                </button>
                {cardOwner && <p className="text-sm text-white/50">{isRu ? "Получатель:" : "Egasi:"} <span className="text-white">{cardOwner}</span></p>}
              </div>
            )}

            {visaCardNumber && (
              <div className="space-y-1">
                <p className="text-xs text-white/40">Visa</p>
                <button
                  onClick={() => navigator.clipboard?.writeText(visaCardNumber)}
                  className="w-full text-left font-mono text-lg font-bold text-white bg-white/5 rounded-xl px-4 py-3 hover:bg-white/10 transition-colors"
                >
                  {visaCardNumber}
                </button>
                {visaCardOwner && <p className="text-sm text-white/50">{isRu ? "Получатель:" : "Egasi:"} <span className="text-white">{visaCardOwner}</span></p>}
              </div>
            )}

            <p className="text-xs text-white/30 text-center">
              {isRu ? "Нажмите на номер карты чтобы скопировать" : "Karta raqamini ko'chirish uchun bosing"}
            </p>
          </div>
        ) : (
          <div className="glass-card p-5 text-center text-sm text-white/50">
            {isRu ? "⚠️ Реквизиты временно не настроены. Обратитесь в поддержку." : "⚠️ To'lov ma'lumotlari sozlanmagan. Qo'llab-quvvatlash bilan bog'laning."}
          </div>
        )}

        {/* Action */}
        {error && (
          <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-sm text-red-400">
            {error}
          </div>
        )}

        {notified ? (
          <div className="glass-card p-5 text-center space-y-2">
            <div className="text-3xl">⏳</div>
            <p className="font-bold text-white">
              {isRu ? "Заявка отправлена!" : "Ariza yuborildi!"}
            </p>
            <p className="text-sm text-white/60">
              {isRu
                ? "Обычно подтверждаем в течение 1 часа. Кредиты зачислятся автоматически."
                : "Odatda 1 soat ichida tasdiqlanadi. Kreditlar avtomatik qo'shiladi."}
            </p>
          </div>
        ) : (
          <button
            onClick={handlePaid}
            disabled={loading || !parsedPaymentId}
            className="w-full py-4 rounded-2xl bg-brand-primary font-bold text-white text-base disabled:opacity-50 transition-all active:scale-95"
          >
            {loading
              ? (isRu ? "Отправка..." : "Yuborilmoqda...")
              : (isRu ? "✅ Я оплатил" : "✅ To'ladim")}
          </button>
        )}

        <Link href="/plans" className="block text-center text-sm text-white/40 hover:text-white/60 transition-colors py-2">
          {isRu ? "← Вернуться к тарифам" : "← Tariflarga qaytish"}
        </Link>
      </div>
    </main>
  );
}

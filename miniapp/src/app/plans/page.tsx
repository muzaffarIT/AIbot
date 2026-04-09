"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { motion, type Variants } from "framer-motion";
import { ArrowLeft, Zap, CreditCard, Banknote, CheckCircle2, PlusCircle } from "lucide-react";
import { useMiniAppUser } from "@/lib/use-miniapp-user";
import { api } from "@/lib/api";

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.1 } },
};
const itemVariants: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 300, damping: 24 } },
};

const PLANS = [
  {
    id: "start",
    nameRu: "⚡ Light",
    nameUz: "⚡ Light",
    descRu: "Для старта",
    descUz: "Boshlash uchun",
    credits: 150,
    priceUzs: 105_000,
    syntxRu: "Syntx €9 ≈ 115 000 сум",
    syntxUz: "Syntx €9 ≈ 115 000 so'm",
    popular: false,
    btnClass: "bg-white/10 text-white hover:bg-white/20",
  },
  {
    id: "pro",
    nameRu: "💎 Standard",
    nameUz: "💎 Standard",
    descRu: "Самый популярный",
    descUz: "Eng mashhur",
    credits: 400,
    priceUzs: 290_000,
    syntxRu: "Syntx €25 ≈ 320 000 сум",
    syntxUz: "Syntx €25 ≈ 320 000 so'm",
    popular: true,
    btnClass: "bg-green-500 text-white shadow-lg shadow-green-500/30",
  },
  {
    id: "creator",
    nameRu: "🚀 Pro",
    nameUz: "🚀 Pro",
    descRu: "Для контент-мейкеров",
    descUz: "Kontent yaratuvchilar uchun",
    credits: 800,
    priceUzs: 580_000,
    syntxRu: "Syntx €50 ≈ 640 000 сум",
    syntxUz: "Syntx €50 ≈ 640 000 so'm",
    popular: false,
    btnClass: "bg-gradient-to-r from-blue-500 to-cyan-500 text-white shadow-lg shadow-blue-500/30",
  },
  {
    id: "ultra",
    nameRu: "👑 Ultra",
    nameUz: "👑 Ultra",
    descRu: "Без ограничений",
    descUz: "Cheksiz imkoniyatlar",
    credits: 2000,
    priceUzs: 1_390_000,
    syntxRu: "Syntx €119 ≈ 1 523 200 сум",
    syntxUz: "Syntx €119 ≈ 1 523 200 so'm",
    popular: false,
    btnClass: "bg-gradient-to-r from-amber-400 to-orange-500 text-white shadow-lg shadow-orange-500/30",
  },
];

const GEN_PRICES = [
  { icon: "🍌", nameRu: "Nano Banana", nameUz: "Nano Banana", fromRu: "от 5 кр.", fromUz: "5 kr.dan" },
  { icon: "🎬", nameRu: "Veo 3",       nameUz: "Veo 3",       fromRu: "от 30 кр.", fromUz: "30 kr.dan" },
  { icon: "🎥", nameRu: "Kling",       nameUz: "Kling",       fromRu: "от 40 кр.", fromUz: "40 kr.dan" },
];

function fmtUzs(n: number, lang: string) {
  return n.toLocaleString("ru-RU") + (lang === "uz" ? " so'm" : " сум");
}

export default function PlansPage() {
  const { language, backendUser: userData } = useMiniAppUser();
  const router = useRouter();
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null);
  const [buyError, setBuyError] = useState("");
  const [successPlan, setSuccessPlan] = useState<{ name: string; credits: number } | null>(null);

  const uz = language === "uz";
  const uzsBalance = userData?.uzs_balance ?? 0;

  const handleBuy = async (planId: string) => {
    if (!userData?.telegram_user_id) {
      setBuyError(uz ? "Foydalanuvchi topilmadi" : "Пользователь не найден");
      return;
    }
    try {
      setLoadingPlan(planId);
      setBuyError("");
      const result = await api.createManualPayment({
        telegram_user_id: userData.telegram_user_id,
        plan_code: planId,
      });
      router.push(
        `/checkout?paymentId=${result.payment_id}&orderId=${result.order_id}` +
        `&orderNumber=${encodeURIComponent(result.order_number ?? "")}&planName=${encodeURIComponent(result.plan_name ?? "")}` +
        `&credits=${result.credits}&amount=${result.amount}&currency=${encodeURIComponent(result.currency ?? "UZS")}` +
        `&cardNumber=${encodeURIComponent(result.card_number ?? "")}&cardOwner=${encodeURIComponent(result.card_owner ?? "")}` +
        `&visaCardNumber=${encodeURIComponent(result.visa_card_number ?? "")}&visaCardOwner=${encodeURIComponent(result.visa_card_owner ?? "")}` +
        `&alreadyPending=${result.already_pending ? "1" : "0"}`
      );
    } catch {
      setBuyError(uz ? "Xatolik yuz berdi. Qayta urinib ko'ring." : "Ошибка при создании заявки. Попробуйте снова.");
    } finally {
      setLoadingPlan(null);
    }
  };

  const handlePayFromBalance = async (planId: string, planPrice: number) => {
    if (!userData?.telegram_user_id) return;
    if (uzsBalance < planPrice) return;
    try {
      setLoadingPlan(`balance_${planId}`);
      setBuyError("");
      const result = await api.payFromBalance(userData.telegram_user_id, planId);
      setSuccessPlan({ name: result.plan_name, credits: result.credits_added });
    } catch (e: any) {
      setBuyError(e?.message ?? (uz ? "Xatolik yuz berdi" : "Ошибка оплаты с баланса"));
    } finally {
      setLoadingPlan(null);
    }
  };

  return (
    <main className="min-h-screen px-5 pt-6 pb-24 overflow-x-hidden">
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="max-w-md mx-auto space-y-6"
      >
        {/* Header */}
        <motion.div variants={itemVariants} className="flex items-center gap-3">
          <Link
            href="/"
            className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-colors"
          >
            <ArrowLeft className="text-white" size={20} />
          </Link>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            {language === "uz" ? "Tariflar" : "Тарифы"}
          </h1>
        </motion.div>

        {/* Success screen */}
        {successPlan && (
          <motion.div variants={itemVariants} className="glass-card p-6 text-center space-y-4">
            <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mx-auto">
              <CheckCircle2 size={36} className="text-green-400" />
            </div>
            <div>
              <h2 className="text-xl font-black text-white">{uz ? "Muvaffaqiyatli!" : "Успешно!"}</h2>
              <p className="text-white/60 text-sm mt-1">
                {uz
                  ? `${successPlan.name} — ${successPlan.credits} kredit hisobingizga qo'shildi`
                  : `${successPlan.name} — ${successPlan.credits} кредитов начислено`}
              </p>
            </div>
            <Link href="/"
              className="block py-3 px-6 rounded-2xl font-bold text-white text-sm"
              style={{ background: "linear-gradient(135deg, #10b981, #059669)" }}
            >
              {uz ? "Bosh sahifaga" : "На главную"}
            </Link>
          </motion.div>
        )}

        {/* UZS balance notice */}
        {uzsBalance > 0 && !successPlan && (
          <motion.div variants={itemVariants}
            className="flex items-center gap-3 p-4 rounded-2xl bg-green-500/10 border border-green-500/20"
          >
            <Banknote className="text-green-400 shrink-0" size={20} />
            <p className="text-sm text-green-300">
              {uz
                ? `So'm balansida: ${fmtUzs(uzsBalance, "uz")} — tarif uchun to'g'ridan-to'g'ri foydalanishingiz mumkin`
                : `На балансе: ${fmtUzs(uzsBalance, "ru")} — можно оплатить тариф напрямую`}
            </p>
          </motion.div>
        )}

        {/* UZS Balance top-up card */}
        {!successPlan && (
          <motion.div variants={itemVariants} className="glass-card p-5 border-green-500/30">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="w-9 h-9 rounded-xl bg-green-500/15 flex items-center justify-center">
                  <Banknote className="text-green-400" size={18} />
                </div>
                <div>
                  <p className="text-sm font-bold text-white">
                    {uz ? "So'm balansi" : "Денежный баланс (сум)"}
                  </p>
                  <p className="text-xs text-white/40">
                    {uz ? "Balansdan to'g'ridan-to'g'ri to'lang" : "Оплачивайте тарифы напрямую"}
                  </p>
                </div>
              </div>
              <p className="text-base font-black text-green-400">
                {fmtUzs(uzsBalance, language)}
              </p>
            </div>
            <Link
              href="/topup"
              className="flex items-center justify-center gap-2 w-full py-3 rounded-xl font-bold text-sm text-white transition-all active:scale-95"
              style={{ background: "linear-gradient(135deg, #10b981, #059669)", boxShadow: "0 4px 14px rgba(16,185,129,0.25)" }}
            >
              <PlusCircle size={16} />
              {uz ? "Balansni to'ldirish" : "Пополнить баланс в сумах"}
            </Link>
          </motion.div>
        )}

        {/* Payment notice */}
        {!successPlan && (
        <motion.div
          variants={itemVariants}
          className="flex items-center gap-3 p-4 rounded-2xl bg-white/5 border border-white/10"
        >
          <CreditCard className="text-brand-cyan shrink-0" size={22} />
          <p className="text-sm text-white/70">
            {uz
              ? "To'lov karta orqali. Tanlangandan so'ng karta raqami ko'rsatiladi."
              : "Оплата по карте. После выбора появятся реквизиты для оплаты."}
          </p>
        </motion.div>
        )}

        {buyError && (
          <motion.div variants={itemVariants} className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-sm text-red-400">
            {buyError}
          </motion.div>
        )}

        {/* Packages */}
        {!successPlan && <motion.div variants={itemVariants} className="space-y-4">
          {PLANS.map((plan) => (
            <div
              key={plan.id}
              className={`glass-card p-5 relative overflow-hidden transition-all ${
                plan.popular
                  ? "border-green-500/60 shadow-lg shadow-green-500/15"
                  : "border-white/5"
              }`}
            >
              {plan.popular && (
                <div className="absolute top-0 right-4 -translate-y-1/2 bg-brand-primary text-white text-[10px] font-bold px-3 py-1 rounded-full tracking-wider uppercase shadow-md">
                  {language === "uz" ? "MASHHUR" : "ПОПУЛЯРНЫЙ"}
                </div>
              )}

              <div className="flex flex-col gap-3">
                {/* Name + credits row */}
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="font-bold text-white text-lg">
                      {language === "uz" ? plan.nameUz : plan.nameRu}
                    </h2>
                    <p className="text-sm text-white/50">
                      {language === "uz" ? plan.descUz : plan.descRu}
                    </p>
                  </div>
                  <p className="text-sm font-semibold text-brand-cyan flex items-center gap-1 shrink-0 ml-3 mt-1">
                    <Zap size={14} />
                    {plan.credits} {language === "uz" ? "kr." : "кр."}
                  </p>
                </div>

                {/* Pricing comparison */}
                <div className="flex flex-col gap-0.5">
                  {/* Syntx comparison — strikethrough */}
                  <p className="text-xs text-white/35 line-through">
                    {language === "uz" ? plan.syntxUz : plan.syntxRu}
                  </p>
                  {/* Our price */}
                  <p className="text-xl font-extrabold text-green-400">
                    {fmtUzs(plan.priceUzs, language)}
                  </p>
                  {/* Credits never expire badge */}
                  <p className="text-xs text-white/50 mt-0.5">
                    {language === "uz" ? "Kreditlar muddatsiz ✅" : "Кредиты не сгорают ✅"}
                  </p>
                </div>

                {/* Pay from UZS balance if sufficient */}
                {uzsBalance >= plan.priceUzs && (
                  <button
                    onClick={() => handlePayFromBalance(plan.id, plan.priceUzs)}
                    disabled={loadingPlan !== null}
                    className="flex items-center justify-center gap-2 font-bold px-4 py-3 rounded-xl transition-all active:scale-95 w-full disabled:opacity-60 text-white"
                    style={{ background: "linear-gradient(135deg, #10b981, #059669)", boxShadow: "0 4px 16px rgba(16,185,129,0.3)" }}
                  >
                    <Banknote size={16} />
                    {loadingPlan === `balance_${plan.id}`
                      ? (uz ? "Yuklanmoqda..." : "Обработка...")
                      : (uz ? "💵 Balansdan to'lash" : "💵 Оплатить с баланса")}
                  </button>
                )}

                <button
                  onClick={() => handleBuy(plan.id)}
                  disabled={loadingPlan !== null}
                  className={`flex items-center justify-center gap-2 font-bold px-4 py-3 rounded-xl transition-all active:scale-95 w-full disabled:opacity-60 ${plan.btnClass}`}
                >
                  <CreditCard size={16} />
                  {loadingPlan === plan.id
                    ? (uz ? "Yuklanmoqda..." : "Загрузка...")
                    : (uz ? "Sotib olish" : "Купить по карте")}
                </button>
              </div>
            </div>
          ))}
        </motion.div>}

        {/* Generation prices */}
        <motion.div variants={itemVariants} className="space-y-3">
          <h2 className="text-sm font-bold uppercase tracking-wider text-white/40 px-1">
            {language === "uz" ? "Generatsiya narxlari" : "Стоимость генераций"}
          </h2>
          <div className="glass-card divide-y divide-white/5">
            {GEN_PRICES.map((g) => (
              <div key={g.nameRu} className="flex items-center justify-between px-4 py-3">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{g.icon}</span>
                  <span className="text-sm font-medium text-white/80">
                    {language === "uz" ? g.nameUz : g.nameRu}
                  </span>
                </div>
                <span className="text-sm font-bold text-brand-accent">
                  {language === "uz" ? g.fromUz : g.fromRu}
                </span>
              </div>
            ))}
          </div>
          <p className="text-xs text-white/30 text-center px-4">
            {language === "uz" ? "Kreditlar muddatsiz amal qiladi" : "Кредиты бессрочные"}
          </p>
        </motion.div>
      </motion.div>
    </main>
  );
}

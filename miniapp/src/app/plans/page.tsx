"use client";

import Link from "next/link";
import { useState } from "react";
import { motion, type Variants } from "framer-motion";
import { ArrowLeft, Zap, Star, Image as ImageIcon, Video } from "lucide-react";
import { useMiniAppUser } from "@/lib/use-miniapp-user";

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
    emoji: "⚡",
    nameRu: "Start",
    nameUz: "Start",
    descRu: "Для знакомства с нейросетями",
    descUz: "Neyrosetlar bilan tanishish uchun",
    credits: 100,
    stars: 580,
    amount: 7.5,
    popular: false,
    btnClass: "bg-white/10 text-white hover:bg-white/20",
    featuresRu: ["✓ Базовый доступ", "✓ Стандартная очередь"],
    featuresUz: ["✓ Asosiy ruxsat", "✓ Oddiy navbat"],
  },
  {
    id: "pro",
    emoji: "💎",
    nameRu: "Pro",
    nameUz: "Pro",
    descRu: "Для активного использования",
    descUz: "Faol foydalanish uchun",
    credits: 300,
    stars: 1450,
    amount: 22.5,
    popular: true,
    btnClass: "bg-brand-primary text-white shadow-lg shadow-brand-primary/30",
    featuresRu: ["✓ Все нейросети", "✓ Быстрая очередь"],
    featuresUz: ["✓ Barcha neyrosetlar", "✓ Tezkor navbat"],
  },
  {
    id: "creator",
    emoji: "🚀",
    nameRu: "Creator",
    nameUz: "Creator",
    descRu: "Для создателей контента",
    descUz: "Kontent yaratuvchilar uchun",
    credits: 600,
    stars: 2600,
    amount: 45.0,
    popular: false,
    btnClass: "bg-gradient-to-r from-blue-500 to-cyan-500 text-white shadow-lg shadow-blue-500/30",
    featuresRu: ["✓ Все нейросети", "✓ Без ограничений", "✓ Приоритет"],
    featuresUz: ["✓ Barcha neyrosetlar", "✓ Cheklovsiz", "✓ Ustuvorlik"],
  },
  {
    id: "ultra",
    emoji: "👑",
    nameRu: "Ultra",
    nameUz: "Ultra",
    descRu: "Для профессионалов",
    descUz: "Professionallar uchun",
    credits: 1500,
    stars: 5800,
    amount: 112.5,
    popular: false,
    btnClass: "bg-gradient-to-r from-amber-400 to-orange-500 text-white shadow-lg shadow-orange-500/30",
    featuresRu: ["✓ Выделенный сервер", "✓ Все нейросети", "✓ Без очереди"],
    featuresUz: ["✓ Maxsus server", "✓ Barcha neyrosetlar", "✓ Navbatsiz"],
  },
];

const GEN_PRICES = [
  { icon: "🍌", nameRu: "Nano Banana", nameUz: "Nano Banana", fromRu: "от 5 кр.", fromUz: "5 kr.dan" },
  { icon: "🎬", nameRu: "Veo 3",       nameUz: "Veo 3",       fromRu: "от 30 кр.", fromUz: "30 kr.dan" },
  { icon: "🎥", nameRu: "Kling",       nameUz: "Kling",       fromRu: "от 40 кр.", fromUz: "40 kr.dan" },
];

export default function PlansPage() {
  const { language, telegramUser } = useMiniAppUser();
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [selectedPackage, setSelectedPackage] = useState<{ id: string; amount: number } | null>(null);

  const PAYMENTS_ENABLED = {
    click: false,
    payme: false,
    stars: true
  };

  const CLICK_SERVICE_ID = process.env.NEXT_PUBLIC_CLICK_SERVICE_ID;
  const CLICK_MERCHANT_ID = process.env.NEXT_PUBLIC_CLICK_MERCHANT_ID;
  const PAYME_MERCHANT_ID = process.env.NEXT_PUBLIC_PAYME_MERCHANT_ID;

  const handleBuy = (packageId: string, amount: number) => {
    setSelectedPackage({ id: packageId, amount });
    setShowPaymentModal(true);
  };

  const payWithClick = (pkg: { id: string; amount: number }) => {
    const userId = (window as any).Telegram?.WebApp?.initDataUnsafe?.user?.id;
    const amountUZS = Math.round(pkg.amount * 12800);
    const url = `https://my.click.uz/services/pay` +
      `?service_id=${CLICK_SERVICE_ID}` +
      `&merchant_id=${CLICK_MERCHANT_ID}` +
      `&amount=${amountUZS}` +
      `&transaction_param=${userId}:${pkg.id}` +
      `&return_url=${encodeURIComponent(window.location.href)}`;
    window.open(url, '_blank');
  };

  const payWithPayme = (pkg: { id: string; amount: number }) => {
    const userId = (window as any).Telegram?.WebApp?.initDataUnsafe?.user?.id;
    const amountTiyins = Math.round(pkg.amount * 12800 * 100);
    const params = btoa(JSON.stringify({
      m: PAYME_MERCHANT_ID,
      "ac.user_id": String(userId),
      "ac.package_id": pkg.id,
      a: amountTiyins,
      l: "ru"
    }));
    window.open(`https://checkout.paycom.uz/${params}`, '_blank');
  };

  const payWithStars = (pkg: { id: string; amount: number }) => {
    const tg = (window as any).Telegram?.WebApp;
    tg?.sendData?.(JSON.stringify({ action: "buy_plan", package_id: pkg.id }));
    tg?.close?.();
  };

  return (
    <main className="min-h-screen px-5 pt-6 pb-24 overflow-x-hidden">
      <motion.div variants={containerVariants} initial="hidden" animate="visible" className="max-w-md mx-auto space-y-6">

        {/* Header */}
        <motion.div variants={itemVariants} className="flex items-center gap-3">
          <Link href="/" className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-colors">
            <ArrowLeft className="text-white" size={20} />
          </Link>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            {language === "uz" ? "Tariflar" : "Тарифы"}
          </h1>
        </motion.div>

        {/* Packages */}
        <motion.div variants={itemVariants} className="space-y-4">
          {PLANS.map((plan) => (
            <div
              key={plan.id}
              className={`glass-card p-5 relative overflow-hidden transition-all ${
                plan.popular ? "border-brand-primary/50 shadow-lg shadow-brand-primary/10" : "border-white/5"
              }`}
            >
              {plan.popular && (
                <div className="absolute top-0 right-4 -translate-y-1/2 bg-brand-primary text-white text-[10px] font-bold px-3 py-1 rounded-full tracking-wider uppercase shadow-md">
                  {language === "uz" ? "MASHHUR" : "ПОПУЛЯРНЫЙ"}
                </div>
              )}
              
              <div className="flex flex-col gap-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <span className="text-3xl mt-1">{plan.emoji}</span>
                    <div>
                      <h2 className="font-bold text-white text-lg">
                        {language === "uz" ? plan.nameUz : plan.nameRu}
                      </h2>
                      <p className="text-sm text-white/50 mb-1">
                        {language === "uz" ? plan.descUz : plan.descRu}
                      </p>
                      <p className="text-sm font-semibold text-brand-cyan flex items-center gap-1">
                        <Zap size={14} />
                        {plan.credits} {language === "uz" ? "kredit" : "кредитов"}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="flex flex-col pl-11 gap-1">
                  {(language === "uz" ? plan.featuresUz : plan.featuresRu).map((f, i) => (
                    <span key={i} className="text-xs text-white/60">{f}</span>
                  ))}
                </div>

                <button
                  onClick={() => handleBuy(plan.id, plan.amount)}
                  className={`mt-2 flex items-center justify-center gap-1.5 font-bold px-4 py-3 rounded-xl transition-all active:scale-95 w-full ${plan.btnClass}`}
                >
                  <Star size={16} />
                  {plan.stars.toLocaleString()}
                </button>
              </div>
            </div>
          ))}
        </motion.div>

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
            {language === "uz"
              ? "1 ⭐ Telegram Star ≈ 0.013 USD • Kreditlar muddatsiz"
              : "1 ⭐ Telegram Star ≈ 0.013 USD • Кредиты бессрочные"}
          </p>
        </motion.div>

        {showPaymentModal && selectedPackage && (
          <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-5">
            <div className="bg-brand-900 border border-white/10 p-6 rounded-2xl w-full max-w-sm space-y-4 shadow-xl">
              <h3 className="text-lg font-bold text-white text-center">
                {language === "uz" ? "To'lov usulini tanlang" : "Выбери способ оплаты"}
              </h3>
              
              <div className="space-y-3">
                {PAYMENTS_ENABLED.click && (
                  <button onClick={() => payWithClick(selectedPackage)} className="w-full flex items-center gap-3 p-4 bg-white/5 hover:bg-white/10 transition-colors rounded-xl text-white font-medium">
                    <span className="text-xl">💳</span> Click (Uzcard, Humo, Visa)
                  </button>
                )}
                {PAYMENTS_ENABLED.payme && (
                  <button onClick={() => payWithPayme(selectedPackage)} className="w-full flex items-center gap-3 p-4 bg-white/5 hover:bg-white/10 transition-colors rounded-xl text-white font-medium">
                    <span className="text-xl">💳</span> Payme (Humo, Uzcard)
                  </button>
                )}
                {PAYMENTS_ENABLED.stars && (
                  <button onClick={() => payWithStars(selectedPackage)} className="w-full flex items-center gap-3 p-4 bg-brand-primary/20 border border-brand-primary/30 hover:bg-brand-primary/40 transition-colors rounded-xl text-white font-medium shadow-md shadow-brand-primary/20">
                    <Star className="text-brand-accent fill-brand-accent" size={20} /> Telegram Stars
                  </button>
                )}
              </div>
              <button 
                onClick={() => setShowPaymentModal(false)}
                className="w-full py-3 mt-2 text-white/50 hover:text-white transition-colors text-sm font-medium"
              >
                {language === "uz" ? "Bekor qilish" : "Отмена"}
              </button>
            </div>
          </div>
        )}

      </motion.div>
    </main>
  );
}

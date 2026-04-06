"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { motion, type Variants } from "framer-motion";
import { ArrowLeft, Copy, Share2, Check, Users, Zap, TrendingUp } from "lucide-react";
import { useTelegramAuth } from "@/hooks/useTelegramAuth";
import { useMiniAppUser } from "@/lib/use-miniapp-user";
import { api } from "@/lib/api";

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
};
const itemVariants: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 300, damping: 24 } },
};

export default function ReferralPage() {
  const { tgUser, userData } = useTelegramAuth();
  const { language } = useMiniAppUser();
  const [refLink, setRefLink] = useState("");
  const [stats, setStats] = useState({ count: 0, earned: 0 });
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const id = userData?.telegram_user_id ?? tgUser?.id;
    if (!id) { setLoading(false); return; }
    api.getReferral(id)
      .then((data) => {
        if (data.referral_code) {
          setRefLink(`https://t.me/harfai_bot?start=ref_${data.referral_code}`);
        }
        setStats({ count: data.referral_count ?? 0, earned: data.referral_earnings ?? 0 });
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [userData?.telegram_user_id, tgUser?.id]);

  const copyLink = async () => {
    if (!refLink) return;
    try { await navigator.clipboard.writeText(refLink); }
    catch {
      const el = document.createElement("textarea");
      el.value = refLink;
      document.body.appendChild(el);
      el.select();
      document.execCommand("copy");
      document.body.removeChild(el);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const shareLink = () => {
    if (!refLink) return;
    const text = encodeURIComponent(
      language === "uz"
        ? "🤖 HARF AI — telefoningizda sun'iy intellekt!\nRasm va videolarni sekundlar ichida yarating.\nRo'yxatdan o'ting va 5 kredit oling:"
        : "🤖 HARF AI — нейросети в твоём телефоне!\nСоздавай картинки и видео за секунды.\nРегистрируйся и получи 5 бесплатных кредитов:"
    );
    const tg = (window as any).Telegram?.WebApp;
    if (tg?.openTelegramLink) {
      tg.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(refLink)}&text=${text}`);
    } else {
      window.open(`https://t.me/share/url?url=${encodeURIComponent(refLink)}&text=${text}`, "_blank");
    }
  };

  const steps = language === "uz"
    ? [
        { icon: "🔗", title: "Havolani ulashing", desc: "Do'stingizga referal havolangizni yuboring" },
        { icon: "👤", title: "Do'stingiz ro'yxatdan o'tadi", desc: "U HARF AI ga qo'shiladi va kredit oladi" },
        { icon: "💰", title: "10% komissiya olasiz", desc: "Uning har bir to'lovidan 10% kredit sizga tushadi" },
      ]
    : [
        { icon: "🔗", title: "Поделитесь ссылкой", desc: "Отправьте реферальную ссылку другу" },
        { icon: "👤", title: "Друг регистрируется", desc: "Он присоединяется к HARF AI и получает кредиты" },
        { icon: "💰", title: "Вы получаете 10%", desc: "С каждого его пополнения вам начисляется 10% кредитов" },
      ];

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-brand-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <main className="min-h-screen px-5 pt-6 pb-28 overflow-x-hidden">
      {/* Ambient */}
      <div className="fixed top-10 right-0 w-72 h-72 bg-green-500/10 blur-[120px] -z-10 rounded-full pointer-events-none" />
      <div className="fixed bottom-20 left-0 w-56 h-56 bg-brand-primary/10 blur-[100px] -z-10 rounded-full pointer-events-none" />

      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="max-w-md mx-auto space-y-6"
      >
        {/* Header */}
        <motion.div variants={itemVariants} className="flex items-center gap-3">
          <Link href="/" className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-colors">
            <ArrowLeft className="text-white" size={20} />
          </Link>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            {language === "uz" ? "Hamkorlik dasturi" : "Партнёрская программа"}
          </h1>
        </motion.div>

        {/* Hero banner — 10% commission */}
        <motion.div variants={itemVariants}>
          <div
            className="relative rounded-3xl overflow-hidden p-6 border border-white/10"
            style={{
              background: "linear-gradient(135deg, rgba(16,185,129,0.25) 0%, rgba(16,16,32,0.95) 60%, rgba(124,58,237,0.15) 100%)",
              boxShadow: "0 0 60px rgba(16,185,129,0.12), inset 0 0 0 1px rgba(255,255,255,0.06)",
            }}
          >
            <div className="absolute -top-10 -right-10 w-36 h-36 rounded-full border border-green-500/15 pointer-events-none" />
            <div className="absolute -top-4 -right-4 w-20 h-20 rounded-full border border-green-500/10 pointer-events-none" />

            <div className="flex items-start gap-4">
              <div
                className="w-16 h-16 rounded-2xl flex items-center justify-center shrink-0 text-2xl font-black text-green-400"
                style={{ background: "rgba(16,185,129,0.15)", border: "1px solid rgba(16,185,129,0.25)" }}
              >
                10%
              </div>
              <div>
                <p className="text-lg font-extrabold text-white leading-tight">
                  {language === "uz"
                    ? "Har bir to'lovdan\n10% kredit oling"
                    : "Получайте 10% кредитов\nс каждого пополнения"}
                </p>
                <p className="text-sm text-white/50 mt-1">
                  {language === "uz"
                    ? "Do'stingiz 400 kr. to'lasa → siz +40 kr. olasiz"
                    : "Друг купил 400 кр. → вам +40 кр. автоматически"}
                </p>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Stats */}
        <motion.div variants={itemVariants} className="grid grid-cols-2 gap-3">
          <div className="glass-card p-5 text-center relative overflow-hidden">
            <div className="absolute top-2 right-2 opacity-10">
              <Users size={40} />
            </div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-white/40 mb-1">
              {language === "uz" ? "Taklif qilingan" : "Приглашено"}
            </p>
            <p className="text-4xl font-extrabold text-white">{stats.count}</p>
            <p className="text-xs text-white/30 mt-1">
              {language === "uz" ? "do'st" : "друзей"}
            </p>
          </div>
          <div className="glass-card p-5 text-center relative overflow-hidden">
            <div className="absolute top-2 right-2 opacity-10">
              <TrendingUp size={40} />
            </div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-white/40 mb-1">
              {language === "uz" ? "Komissiya" : "Заработано"}
            </p>
            <p className="text-4xl font-extrabold text-green-400">{stats.earned}</p>
            <p className="text-xs text-white/30 mt-1">
              {language === "uz" ? "kredit" : "кредитов"}
            </p>
          </div>
        </motion.div>

        {/* Referral link card */}
        <motion.div variants={itemVariants} className="glass-card p-5 space-y-4">
          <p className="text-xs font-bold uppercase tracking-wider text-white/40">
            {language === "uz" ? "Sizning havolangiz" : "Ваша ссылка"}
          </p>
          {refLink ? (
            <div
              className="px-4 py-3 rounded-2xl text-sm font-mono break-all"
              style={{ background: "rgba(124,58,237,0.1)", border: "1px solid rgba(124,58,237,0.2)" }}
            >
              <span className="text-brand-primary">{refLink}</span>
            </div>
          ) : (
            <div className="px-4 py-3 rounded-2xl text-sm text-white/30 italic"
              style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
              {language === "uz" ? "Havola topilmadi" : "Ссылка недоступна"}
            </div>
          )}
          <div className="flex gap-3">
            <button
              onClick={copyLink}
              disabled={!refLink}
              className={`flex-1 flex items-center justify-center gap-2 py-3.5 rounded-2xl text-sm font-bold transition-all active:scale-95 disabled:opacity-40 ${
                copied
                  ? "bg-green-500 text-white"
                  : "bg-brand-primary text-white hover:opacity-90"
              }`}
            >
              {copied ? <Check size={16} /> : <Copy size={16} />}
              {copied
                ? (language === "uz" ? "Nusxalandi!" : "Скопировано!")
                : (language === "uz" ? "Nusxalash" : "Скопировать")}
            </button>
            <button
              onClick={shareLink}
              disabled={!refLink}
              className="flex-1 flex items-center justify-center gap-2 py-3.5 rounded-2xl text-sm font-bold bg-white/8 text-white hover:bg-white/12 transition-all active:scale-95 disabled:opacity-40"
            >
              <Share2 size={16} />
              {language === "uz" ? "Ulashish" : "Поделиться"}
            </button>
          </div>
        </motion.div>

        {/* How it works */}
        <motion.div variants={itemVariants} className="space-y-3">
          <h2 className="text-sm font-bold uppercase tracking-wider text-white/40 px-1">
            {language === "uz" ? "Qanday ishlaydi" : "Как это работает"}
          </h2>
          <div className="space-y-2">
            {steps.map((step, i) => (
              <div key={i} className="glass-card px-4 py-4 flex items-start gap-4">
                <div
                  className="w-10 h-10 rounded-2xl flex items-center justify-center text-xl shrink-0"
                  style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}
                >
                  {step.icon}
                </div>
                <div>
                  <p className="text-sm font-bold text-white">{step.title}</p>
                  <p className="text-xs text-white/45 mt-0.5 leading-relaxed">{step.desc}</p>
                </div>
                <span className="ml-auto text-xs font-black text-white/15 self-center shrink-0">
                  {i + 1}
                </span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Also earns */}
        <motion.div variants={itemVariants}>
          <div className="glass-card px-4 py-4 flex items-center gap-3">
            <Zap className="text-brand-cyan shrink-0" size={18} />
            <p className="text-xs text-white/60">
              {language === "uz"
                ? "Har bir yangi do'stingiz ham +5 kredit oladi. Hamkorlikda ikkalangiz yutasiz!"
                : "Ваш друг также получает +5 кредитов при регистрации. Выгода для обоих!"}
            </p>
          </div>
        </motion.div>
      </motion.div>
    </main>
  );
}

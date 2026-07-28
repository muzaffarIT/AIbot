"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import { motion, type Variants } from "framer-motion";
import {
  ArrowLeft, Trophy, Lock, Calendar,
  Globe, Check, Zap, Users, CreditCard, Gift,
  Wallet, ClipboardList, ChevronDown, LifeBuoy, Sparkles,
} from "lucide-react";
import { useMiniAppUser } from "@/lib/use-miniapp-user";
import { api, type AchievementItem } from "@/lib/api";

const SUPPORT_USERNAME = "khaetov_000";

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
};
const itemVariants: Variants = {
  hidden: { opacity: 0, y: 15 },
  visible: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 300, damping: 24 } },
};

const LANG_OPTIONS = [
  { code: "ru", label: "Русский 🇷🇺" },
  { code: "uz", label: "O'zbekcha 🇺🇿" },
];

export default function ProfilePage() {
  const { telegramUser: tgUser, backendUser: userData, loading, language, changeLanguage } = useMiniAppUser();
  const [langMenuOpen, setLangMenuOpen] = useState(false);
  const [communityOpen, setCommunityOpen] = useState(false);
  const [achievements, setAchievements] = useState<AchievementItem[]>([]);

  useEffect(() => {
    const id = userData?.telegram_user_id ?? tgUser?.id;
    if (!id) return;
    api.getAchievements(id)
      .then(setAchievements)
      .catch(() => {});
  }, [userData?.telegram_user_id, tgUser?.id]);

  const handleLangChange = (code: string) => {
    changeLanguage(code);
    setLangMenuOpen(false);
  };

  const displayName =
    tgUser?.first_name ||
    userData?.first_name ||
    userData?.username ||
    (language === "uz" ? "Foydalanuvchi" : "Пользователь");

  const credits = userData?.credits_balance ?? 0;
  const referralCount = userData?.referral_count ?? 0;
  const registeredAt = userData?.created_at ?? null;
  const earnedCount = achievements.filter((a) => a.earned).length;

  const formatDate = (d: string) =>
    new Date(d).toLocaleDateString(language === "uz" ? "uz-UZ" : "ru-RU", {
      year: "numeric", month: "long", day: "numeric",
    });

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-brand-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <main className="min-h-screen px-5 pt-6 pb-24 overflow-x-hidden">
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="max-w-md mx-auto space-y-6"
      >
        {/* Header */}
        <motion.div variants={itemVariants} className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-colors"
            >
              <ArrowLeft className="text-white" size={20} />
            </Link>
            <h1 className="text-2xl font-bold text-white tracking-tight">
              {language === "uz" ? "Profil" : "Профиль"}
            </h1>
          </div>

          {/* Language switcher */}
          <div className="relative">
            <button
              onClick={() => setLangMenuOpen(!langMenuOpen)}
              className="flex items-center gap-1.5 px-3 py-2 rounded-full bg-white/5 text-white/70 hover:bg-white/10 transition-colors text-sm"
            >
              <Globe size={16} />
              {language === "uz" ? "UZ" : "RU"}
            </button>
            {langMenuOpen && (
              <div className="absolute right-0 top-10 z-50 bg-brand-900 border border-white/10 rounded-2xl overflow-hidden shadow-xl shadow-black/40 min-w-[150px]">
                {LANG_OPTIONS.map((opt) => (
                  <button
                    key={opt.code}
                    onClick={() => handleLangChange(opt.code)}
                    className="w-full flex items-center gap-2 px-4 py-3 hover:bg-white/5 transition-colors text-sm text-white/90"
                  >
                    {language === opt.code && <Check size={14} className="text-brand-cyan" />}
                    {opt.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </motion.div>

        {/* Dashboard — identity + balance on the left, quick actions on the
            right, so the whole account fits one screenful (Syntx-style). */}
        <motion.section variants={itemVariants} className="grid grid-cols-2 gap-3">
          <div className="glass-card p-4 flex flex-col justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-primary to-brand-cyan flex items-center justify-center text-white text-base font-bold shrink-0">
                {displayName.charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-bold text-white truncate">{displayName}</p>
                {(tgUser?.username || userData?.username) && (
                  <p className="text-[11px] text-white/40 truncate">
                    @{tgUser?.username || userData?.username}
                  </p>
                )}
              </div>
            </div>
            <div className="mt-4">
              <div className="flex items-baseline gap-1.5">
                <span className="text-4xl font-black text-white tracking-tight tabular-nums">
                  {credits}
                </span>
                <Zap size={18} className="text-brand-accent" />
              </div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-white/40 mt-0.5">
                {language === "uz" ? "Kredit balansi" : "Баланс кредитов"}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <QuickTile href="/plans" icon={<CreditCard size={18} />}
              label={language === "uz" ? "Tariflar" : "Тарифы"} />
            <QuickTile href="/wallet" icon={<Wallet size={18} />}
              label={language === "uz" ? "Hamyon" : "Кошелёк"} />
            <QuickTile href="/referral" icon={<Users size={18} />}
              label={language === "uz" ? "Hamkorlik" : "Партнёрам"}
              badge={referralCount || undefined} />
            <QuickTile href="/jobs" icon={<ClipboardList size={18} />}
              label={language === "uz" ? "Ishlarim" : "Работы"} />
          </div>
        </motion.section>

        {/* Community — support + channels, collapsed by default */}
        <motion.section variants={itemVariants} className="glass-card overflow-hidden">
          <button
            onClick={() => setCommunityOpen((v) => !v)}
            className="w-full flex items-center justify-between px-4 py-3.5"
          >
            <span className="text-sm font-bold text-white">
              {language === "uz" ? "Jamiyatga qo'shiling" : "Присоединяйтесь"}
            </span>
            <ChevronDown
              size={18}
              className={`text-white/40 transition-transform ${communityOpen ? "rotate-180" : ""}`}
            />
          </button>
          {communityOpen && (
            <div className="px-2 pb-2 space-y-1">
              <a
                href={`https://t.me/${SUPPORT_USERNAME}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/5 transition-colors"
              >
                <LifeBuoy size={16} className="text-brand-cyan shrink-0" />
                <span className="text-sm text-white/80">
                  {language === "uz" ? "Yordam va qo'llab-quvvatlash" : "Помощь и поддержка"}
                </span>
              </a>
              <Link
                href="/plans"
                className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/5 transition-colors"
              >
                <Sparkles size={16} className="text-brand-accent shrink-0" />
                <span className="text-sm text-white/80">
                  {language === "uz" ? "Tariflar va imkoniyatlar" : "Тарифы и возможности"}
                </span>
              </Link>
            </div>
          )}
        </motion.section>

        {/* Achievements */}
        <motion.div variants={itemVariants} className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Trophy size={18} className="text-brand-accent" />
              {language === "uz" ? "Yutuqlar" : "Достижения"}
            </h2>
            <span className="text-xs text-white/40 font-medium">
              {earnedCount}/{achievements.length || 8}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {(achievements.length
              ? achievements
              : Array.from({ length: 8 }, (_, i) => ({
                  code: `a${i}`,
                  name: "...",
                  emoji: "🏆",
                  bonus: 0,
                  earned: false,
                }))
            ).map((a) => (
              <div
                key={a.code}
                className={`glass-card p-4 relative overflow-hidden transition-all ${
                  a.earned ? "border-brand-accent/30 bg-brand-accent/5" : "border-white/5"
                }`}
                style={{ opacity: a.earned ? 1 : 0.4 }}
              >
                <div className="flex items-start gap-3">
                  <span className="text-2xl">{a.emoji}</span>
                  <div className="flex-1 min-w-0">
                    <p className={`text-xs font-semibold leading-tight ${a.earned ? "text-white" : "text-white/50"}`}>
                      {language === "uz" ? ((a as any).name_uz || a.name) : ((a as any).name_ru || a.name)}
                    </p>
                    {a.bonus > 0 && (
                      <p className="text-[10px] text-brand-accent font-bold mt-0.5">+{a.bonus} {language === "uz" ? "kr." : "кр."}</p>
                    )}
                  </div>
                  {a.earned ? (
                    <Check size={14} className="text-brand-accent flex-shrink-0" />
                  ) : (
                    <Lock size={12} className="text-white/20 flex-shrink-0" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Quick links */}
        <motion.div variants={itemVariants} className="space-y-2">
          <Link
            href="/referral"
            className="glass-card p-4 flex items-center gap-4 hover:bg-white/5 transition-colors"
          >
            <Gift size={20} className="text-brand-primary" />
            <span className="text-sm font-medium text-white/80">
              {language === "uz" ? "Referal dasturi" : "Реферальная программа"}
            </span>
          </Link>
          <Link
            href="/wallet"
            className="glass-card p-4 flex items-center gap-4 hover:bg-white/5 transition-colors"
          >
            <CreditCard size={20} className="text-brand-cyan" />
            <span className="text-sm font-medium text-white/80">
              {language === "uz" ? "Balans va to'lovlar" : "Баланс и платежи"}
            </span>
          </Link>
        </motion.div>

        {/* Support footer — the details support asks for first */}
        <motion.p
          variants={itemVariants}
          className="text-center text-[11px] text-white/25 tabular-nums pt-1"
        >
          {registeredAt && (
            <>
              <Calendar size={10} className="inline mb-0.5 mr-1" />
              {language === "uz" ? "Ro'yxatdan o'tgan" : "Регистрация"}: {formatDate(registeredAt)}
              {" · "}
            </>
          )}
          ID: {userData?.telegram_user_id ?? tgUser?.id ?? "—"}
        </motion.p>
      </motion.div>
    </main>
  );
}

/** Compact square action tile for the profile dashboard. */
function QuickTile({
  href, icon, label, badge,
}: {
  href: string;
  icon: React.ReactNode;
  label: string;
  badge?: number;
}) {
  return (
    <Link
      href={href}
      className="glass-panel relative flex flex-col items-center justify-center gap-1.5 aspect-square hover:bg-white/8 transition-colors active:scale-95"
    >
      <span className="text-brand-cyan">{icon}</span>
      <span className="text-[11px] font-semibold text-white/75 text-center leading-tight px-1">
        {label}
      </span>
      {badge !== undefined && badge > 0 && (
        <span className="absolute top-1.5 right-1.5 min-w-[18px] h-[18px] px-1 rounded-full bg-brand-primary text-[10px] font-bold text-white grid place-items-center tabular-nums">
          {badge}
        </span>
      )}
    </Link>
  );
}

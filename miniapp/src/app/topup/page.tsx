"use client";

import Link from "next/link";
import { useState, useEffect, useRef } from "react";
import { motion, type Variants } from "framer-motion";
import { ArrowLeft, Banknote, Copy, CheckCircle2, Loader2, CreditCard } from "lucide-react";
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

const PRESETS = [10_000, 25_000, 50_000, 100_000, 250_000, 500_000];

type Step = "amount" | "card" | "success";

type CardDetails = {
  card_number: string;
  card_owner: string;
  visa_card_number: string;
  visa_card_owner: string;
};

function fmtUzs(n: number) {
  return n.toLocaleString("uz-UZ");
}

function CopyBtn({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };
  return (
    <button
      onClick={handleCopy}
      className="ml-2 p-1.5 rounded-lg bg-white/10 hover:bg-white/20 transition-colors"
    >
      {copied ? <CheckCircle2 size={14} className="text-green-400" /> : <Copy size={14} className="text-white/50" />}
    </button>
  );
}

export default function TopupPage() {
  const { backendUser: userData, telegramUser: tgUser, language } = useMiniAppUser();
  const uz = language === "uz";

  const [step, setStep] = useState<Step>("amount");
  const [amount, setAmount] = useState<number | "">("");
  const [customInput, setCustomInput] = useState("");
  const [cards, setCards] = useState<CardDetails | null>(null);
  const [cardsLoading, setCardsLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [receiptFile, setReceiptFile] = useState<File | null>(null);
  const [receiptPreview, setReceiptPreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const tgId = userData?.telegram_user_id ?? tgUser?.id ?? 0;

  useEffect(() => {
    if (step === "card" && !cards) {
      setCardsLoading(true);
      api.getCardDetails()
        .then(setCards)
        .catch(() => setError(uz ? "Karta ma'lumotlarini yuklab bo'lmadi" : "Не удалось загрузить реквизиты"))
        .finally(() => setCardsLoading(false));
    }
  }, [step]);

  const selectedAmount = typeof amount === "number" ? amount : parseInt(customInput.replace(/\D/g, "")) || 0;

  const handleSelectPreset = (val: number) => {
    setAmount(val);
    setCustomInput("");
  };

  const handleCustomChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value.replace(/\D/g, "");
    setCustomInput(raw);
    setAmount("");
  };

  const canProceed = selectedAmount >= 5_000;

  const handleContinue = () => {
    if (!canProceed) return;
    setStep("card");
  };

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    setReceiptFile(file);
    if (file && file.type.startsWith("image/")) {
      setReceiptPreview(URL.createObjectURL(file));
    } else {
      setReceiptPreview(null);
    }
  }

  function handleRemoveReceipt() {
    setReceiptFile(null);
    setReceiptPreview(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  const handleConfirmPaid = async () => {
    if (!tgId || submitting || !receiptFile) return;
    setSubmitting(true);
    setError("");
    try {
      await api.uzsTopupNotify(tgId, selectedAmount, receiptFile);
      setStep("success");
    } catch (e: any) {
      setError(e?.message || (uz ? "Xatolik yuz berdi" : "Произошла ошибка"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen px-5 pt-6 pb-28 overflow-x-hidden">
      <div className="fixed top-0 left-0 w-72 h-72 bg-green-500/10 blur-[120px] -z-10 rounded-full pointer-events-none" />
      <div className="fixed bottom-20 right-0 w-56 h-56 bg-brand-cyan/8 blur-[100px] -z-10 rounded-full pointer-events-none" />

      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="max-w-md mx-auto space-y-6"
      >
        {/* Header */}
        <motion.div variants={itemVariants} className="flex items-center gap-3">
          <Link
            href="/wallet"
            className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-colors"
          >
            <ArrowLeft className="text-white" size={20} />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">
              {uz ? "Balansni to'ldirish" : "Пополнение баланса"}
            </h1>
            <p className="text-xs text-white/40 mt-0.5">
              {uz ? "So'm balansi (UZS)" : "Денежный баланс (UZS)"}
            </p>
          </div>
        </motion.div>

        {/* Step: amount */}
        {step === "amount" && (
          <>
            <motion.div variants={itemVariants}>
              <p className="text-sm text-white/50 mb-3 px-1">
                {uz ? "Miqdorni tanlang" : "Выберите сумму"}
              </p>
              <div className="grid grid-cols-3 gap-2">
                {PRESETS.map((val) => (
                  <button
                    key={val}
                    onClick={() => handleSelectPreset(val)}
                    className={`py-3 rounded-2xl text-sm font-bold transition-all active:scale-95 border ${
                      amount === val
                        ? "bg-green-500/20 border-green-500/60 text-green-400"
                        : "bg-white/5 border-white/10 text-white/70 hover:bg-white/10"
                    }`}
                  >
                    {fmtUzs(val)}
                  </button>
                ))}
              </div>
            </motion.div>

            <motion.div variants={itemVariants}>
              <p className="text-sm text-white/50 mb-2 px-1">
                {uz ? "Yoki o'z miqdoringizni kiriting" : "Или введите свою сумму"}
              </p>
              <div className="relative">
                <input
                  type="text"
                  inputMode="numeric"
                  value={customInput}
                  onChange={handleCustomChange}
                  placeholder={uz ? "Masalan: 75000" : "Например: 75000"}
                  className="w-full bg-white/5 border border-white/10 rounded-2xl px-4 py-3.5 text-white placeholder-white/20 text-base font-semibold focus:outline-none focus:border-green-500/50 focus:bg-white/8 transition-colors pr-16"
                />
                <span className="absolute right-4 top-1/2 -translate-y-1/2 text-white/30 text-sm font-bold">
                  {uz ? "so'm" : "сум"}
                </span>
              </div>
              {selectedAmount > 0 && selectedAmount < 5_000 && (
                <p className="text-xs text-red-400 mt-1.5 px-1">
                  {uz ? "Minimal: 5 000 so'm" : "Минимум: 5 000 сум"}
                </p>
              )}
            </motion.div>

            {selectedAmount >= 5_000 && (
              <motion.div variants={itemVariants}
                className="p-4 rounded-2xl bg-green-500/10 border border-green-500/20 text-center"
              >
                <p className="text-xs text-white/40 mb-1">
                  {uz ? "To'lov miqdori" : "Сумма к оплате"}
                </p>
                <p className="text-3xl font-black text-green-400">
                  {fmtUzs(selectedAmount)} {uz ? "so'm" : "сум"}
                </p>
              </motion.div>
            )}

            <motion.div variants={itemVariants}>
              <button
                onClick={handleContinue}
                disabled={!canProceed}
                className="w-full py-4 rounded-2xl font-bold text-base transition-all active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed"
                style={{
                  background: canProceed ? "linear-gradient(135deg, #10b981, #059669)" : undefined,
                  backgroundColor: canProceed ? undefined : "rgba(255,255,255,0.05)",
                  boxShadow: canProceed ? "0 4px 20px rgba(16,185,129,0.4)" : undefined,
                }}
              >
                <div className="flex items-center justify-center gap-2 text-white">
                  <CreditCard size={18} />
                  {uz ? "Davom etish" : "Продолжить"}
                </div>
              </button>
            </motion.div>
          </>
        )}

        {/* Step: card details */}
        {step === "card" && (
          <>
            <motion.div variants={itemVariants}
              className="p-4 rounded-2xl bg-green-500/10 border border-green-500/20 text-center"
            >
              <p className="text-xs text-white/40 mb-1">
                {uz ? "To'lov miqdori" : "Сумма к оплате"}
              </p>
              <p className="text-3xl font-black text-green-400">
                {fmtUzs(selectedAmount)} {uz ? "so'm" : "сум"}
              </p>
            </motion.div>

            <motion.div variants={itemVariants}>
              <p className="text-sm font-bold text-white/50 uppercase tracking-wider mb-3 px-1">
                {uz ? "Karta rekvizitlari" : "Реквизиты для оплаты"}
              </p>

              {cardsLoading ? (
                <div className="p-10 flex justify-center">
                  <Loader2 size={24} className="animate-spin text-green-400" />
                </div>
              ) : (
                <div className="space-y-3">
                  {cards?.card_number && (
                    <div className="glass-card p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Banknote size={14} className="text-white/40" />
                        <p className="text-xs font-bold text-white/40 uppercase tracking-wider">Humo / Uzcard</p>
                      </div>
                      <div className="flex items-center justify-between">
                        <p className="text-lg font-mono font-bold text-white tracking-wider">
                          {cards.card_number}
                        </p>
                        <CopyBtn text={cards.card_number.replace(/\s/g, "")} />
                      </div>
                      {cards.card_owner && (
                        <p className="text-sm text-white/50 mt-1">{cards.card_owner}</p>
                      )}
                    </div>
                  )}

                  {cards?.visa_card_number && (
                    <div className="glass-card p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <CreditCard size={14} className="text-white/40" />
                        <p className="text-xs font-bold text-white/40 uppercase tracking-wider">Visa</p>
                      </div>
                      <div className="flex items-center justify-between">
                        <p className="text-lg font-mono font-bold text-white tracking-wider">
                          {cards.visa_card_number}
                        </p>
                        <CopyBtn text={cards.visa_card_number.replace(/\s/g, "")} />
                      </div>
                      {cards.visa_card_owner && (
                        <p className="text-sm text-white/50 mt-1">{cards.visa_card_owner}</p>
                      )}
                    </div>
                  )}

                  {!cards?.card_number && !cards?.visa_card_number && (
                    <div className="glass-card p-6 text-center">
                      <p className="text-white/40 text-sm">
                        {uz ? "Rekvizitlar vaqtincha mavjud emas" : "Реквизиты временно недоступны"}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </motion.div>

            <motion.div variants={itemVariants}
              className="p-4 rounded-2xl bg-white/5 border border-white/10"
            >
              <p className="text-sm text-white/60 leading-relaxed">
                {uz
                  ? "Yuqoridagi kartalardan biriga to'lovni amalga oshiring va \"Men to'ladim\" tugmasini bosing. Admin tasdiqlaydi."
                  : "Переведите точную сумму на одну из карт выше и нажмите «Я оплатил». Администратор проверит и подтвердит."}
              </p>
            </motion.div>

            {/* Receipt upload */}
            <motion.div variants={itemVariants} className="glass-card p-4 space-y-3">
              <p className="text-xs font-bold text-white/40 uppercase tracking-wider">
                {uz ? "To'lov cheki" : "Чек перевода"}
              </p>
              {receiptFile ? (
                <div className="space-y-2">
                  {receiptPreview ? (
                    <img src={receiptPreview} alt="receipt" className="w-full rounded-xl max-h-48 object-cover" />
                  ) : (
                    <div className="flex items-center gap-3 p-3 rounded-xl bg-white/5">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-white/50 shrink-0">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" strokeLinecap="round" strokeLinejoin="round"/>
                        <polyline points="14 2 14 8 20 8" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                      <span className="text-sm text-white truncate">{receiptFile.name}</span>
                    </div>
                  )}
                  <button
                    onClick={handleRemoveReceipt}
                    className="w-full py-2 rounded-xl bg-white/5 text-white/50 text-sm hover:bg-white/10 transition-colors"
                  >
                    {uz ? "✕ O'chirish va boshqasini tanlash" : "✕ Удалить и выбрать другой"}
                  </button>
                </div>
              ) : (
                <label className="flex flex-col items-center justify-center gap-2 p-5 rounded-xl border-2 border-dashed border-white/15 bg-white/3 cursor-pointer hover:border-white/30 hover:bg-white/5 transition-colors">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*,.pdf,application/pdf"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-white/30">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" strokeLinecap="round" strokeLinejoin="round"/>
                    <polyline points="17 8 12 3 7 8" strokeLinecap="round" strokeLinejoin="round"/>
                    <line x1="12" y1="3" x2="12" y2="15" strokeLinecap="round"/>
                  </svg>
                  <p className="text-sm text-white/50 text-center">
                    {uz ? "Chekni biriktiring" : "Прикрепить скриншот чека"}
                  </p>
                  <p className="text-xs text-white/25 text-center">
                    {uz ? "Rasm yoki PDF" : "Фото или PDF"}
                  </p>
                </label>
              )}
            </motion.div>

            {error && (
              <motion.div variants={itemVariants}
                className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm text-center"
              >
                {error}
              </motion.div>
            )}

            <motion.div variants={itemVariants} className="space-y-3">
              <button
                onClick={handleConfirmPaid}
                disabled={submitting || !receiptFile}
                className="w-full py-4 rounded-2xl font-bold text-base transition-all active:scale-95 disabled:opacity-60"
                style={{
                  background: receiptFile ? "linear-gradient(135deg, #10b981, #059669)" : undefined,
                  backgroundColor: receiptFile ? undefined : "rgba(255,255,255,0.05)",
                  boxShadow: receiptFile ? "0 4px 20px rgba(16,185,129,0.4)" : undefined,
                }}
              >
                <div className="flex items-center justify-center gap-2 text-white">
                  {submitting ? (
                    <Loader2 size={18} className="animate-spin" />
                  ) : (
                    <CheckCircle2 size={18} />
                  )}
                  {submitting
                    ? (uz ? "Yuborilmoqda..." : "Отправляем...")
                    : !receiptFile
                      ? (uz ? "📎 Avval chekni biriktiring" : "📎 Сначала прикрепите чек")
                      : (uz ? "Men to'ladim" : "Я оплатил")}
                </div>
              </button>
              <button
                onClick={() => setStep("amount")}
                className="w-full py-3 rounded-2xl font-semibold text-sm text-white/50 hover:text-white/80 transition-colors"
              >
                {uz ? "Orqaga" : "Назад"}
              </button>
            </motion.div>
          </>
        )}

        {/* Step: success */}
        {step === "success" && (
          <motion.div
            variants={itemVariants}
            className="flex flex-col items-center text-center py-8 space-y-6"
          >
            <div className="w-20 h-20 rounded-full bg-green-500/20 flex items-center justify-center">
              <CheckCircle2 size={44} className="text-green-400" />
            </div>
            <div className="space-y-2">
              <h2 className="text-2xl font-black text-white">
                {uz ? "So'rov yuborildi!" : "Заявка отправлена!"}
              </h2>
              <p className="text-white/50 text-sm leading-relaxed max-w-xs">
                {uz
                  ? `${fmtUzs(selectedAmount)} so'm to'lovi uchun so'rovingiz adminga yuborildi. Tasdiqlanganidan so'ng balansingizga qo'shiladi.`
                  : `Заявка на ${fmtUzs(selectedAmount)} сум отправлена администратору. После проверки средства поступят на ваш баланс.`}
              </p>
            </div>
            <Link
              href="/wallet"
              className="px-8 py-3.5 rounded-2xl font-bold text-sm text-white transition-all active:scale-95"
              style={{
                background: "linear-gradient(135deg, #10b981, #059669)",
                boxShadow: "0 4px 16px rgba(16,185,129,0.35)",
              }}
            >
              {uz ? "Balansga qaytish" : "Вернуться к балансу"}
            </Link>
          </motion.div>
        )}
      </motion.div>
    </main>
  );
}

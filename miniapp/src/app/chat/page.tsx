"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send, Sparkles, ChevronDown, Check, Coins, Brain, Plus, AlertCircle,
} from "lucide-react";
import { useMiniAppUser } from "@/lib/use-miniapp-user";
import { api, type ChatModelInfo, type ChatMessageDTO, ApiError } from "@/lib/api";

type UiMessage = { role: "user" | "assistant"; content: string; pending?: boolean };

const SUGGESTIONS_RU = [
  "Придумай идею для видео в Instagram",
  "Помоги написать текст для поста",
  "Объясни простыми словами, что такое нейросети",
];
const SUGGESTIONS_UZ = [
  "Instagram uchun video g'oyasi o'ylab top",
  "Post uchun matn yozishga yordam ber",
  "Neyrosetlar nima — oddiy tilda tushuntir",
];

export default function ChatPage() {
  const { telegramUser: tgUser, backendUser, language, syncUser } = useMiniAppUser();
  const uz = language === "uz";

  const [models, setModels] = useState<ChatModelInfo[]>([]);
  const [modelId, setModelId] = useState<string>("");
  const [pickerOpen, setPickerOpen] = useState(false);

  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  const scrollRef = useRef<HTMLDivElement>(null);
  const credits = backendUser?.credits_balance ?? 0;
  const activeModel = models.find((m) => m.id === modelId);

  // Load available models
  useEffect(() => {
    api.getChatModels()
      .then((res) => {
        setModels(res.models);
        if (res.models.length) setModelId((prev) => prev || res.models[0].id);
      })
      .catch(() => setError(uz ? "Modellarni yuklab bo'lmadi" : "Не удалось загрузить модели"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Autoscroll to newest message
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = useCallback(
    async (raw: string) => {
      const text = raw.trim();
      if (!text || sending || !modelId || !backendUser?.telegram_user_id) return;
      setError("");
      setInput("");
      setMessages((prev) => [
        ...prev,
        { role: "user", content: text },
        { role: "assistant", content: "", pending: true },
      ]);
      setSending(true);
      try {
        const res = await api.sendChat({
          telegram_user_id: backendUser.telegram_user_id,
          model_id: modelId,
          message: text,
          conversation_id: conversationId,
        });
        setConversationId(res.conversation_id);
        setMessages((prev) => {
          const next = [...prev];
          // replace the trailing pending bubble
          next[next.length - 1] = { role: "assistant", content: res.reply };
          return next;
        });
        void syncUser(); // refresh credit balance
      } catch (e) {
        const msg = e instanceof ApiError ? e.message : uz ? "Xatolik yuz berdi" : "Произошла ошибка";
        setMessages((prev) => prev.slice(0, -1)); // drop pending bubble
        setError(msg);
      } finally {
        setSending(false);
      }
    },
    [sending, modelId, backendUser?.telegram_user_id, conversationId, syncUser, uz],
  );

  function newChat() {
    setMessages([]);
    setConversationId(null);
    setError("");
  }

  const displayName = tgUser?.first_name || (uz ? "Ijodkor" : "Творец");
  const suggestions = uz ? SUGGESTIONS_UZ : SUGGESTIONS_RU;

  return (
    <main className="min-h-screen flex flex-col">
      {/* ── Header: model selector + balance ── */}
      <header className="fixed top-0 left-0 right-0 z-40 bg-brand-900/80 backdrop-blur-xl border-b border-white/10">
        <div className="max-w-md mx-auto px-4 h-14 flex items-center justify-between gap-3">
          <button
            onClick={() => setPickerOpen((v) => !v)}
            className="flex items-center gap-2 min-w-0 px-3 py-2 rounded-xl bg-white/5 border border-white/10 active:scale-95 transition"
          >
            <Sparkles size={16} className="text-brand-cyan shrink-0" />
            <span className="text-sm font-semibold text-white truncate">
              {activeModel?.label ?? (uz ? "Model" : "Модель")}
            </span>
            <ChevronDown size={15} className={`text-white/50 shrink-0 transition ${pickerOpen ? "rotate-180" : ""}`} />
          </button>

          <div className="flex items-center gap-2 shrink-0">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-brand-primary/15 border border-brand-primary/25">
              <Coins size={14} className="text-brand-accent" />
              <span className="text-sm font-bold text-white tabular-nums">{credits}</span>
            </div>
            <button
              onClick={newChat}
              aria-label={uz ? "Yangi suhbat" : "Новый чат"}
              className="w-9 h-9 grid place-items-center rounded-xl bg-white/5 border border-white/10 active:scale-95 transition"
            >
              <Plus size={18} className="text-white/80" />
            </button>
          </div>
        </div>

        {/* Model picker dropdown */}
        <AnimatePresence>
          {pickerOpen && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="max-w-md mx-auto px-4 pb-3"
            >
              <div className="glass-card p-1.5 max-h-[60vh] overflow-y-auto">
                {models.map((m) => {
                  const active = m.id === modelId;
                  return (
                    <button
                      key={m.id}
                      onClick={() => { setModelId(m.id); setPickerOpen(false); }}
                      className={`w-full flex items-start gap-3 p-3 rounded-2xl text-left transition ${active ? "bg-brand-primary/20" : "hover:bg-white/5"}`}
                    >
                      <div className="w-8 h-8 shrink-0 rounded-lg bg-gradient-to-br from-brand-primary to-brand-cyan grid place-items-center">
                        {m.reasoning ? <Brain size={16} className="text-white" /> : <Sparkles size={16} className="text-white" />}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-white">{m.label}</span>
                          {active && <Check size={14} className="text-brand-cyan shrink-0" />}
                        </div>
                        <p className="text-xs text-white/45 leading-snug mt-0.5">{m.description}</p>
                      </div>
                      <span className="shrink-0 text-[11px] font-bold text-brand-accent flex items-center gap-1 mt-0.5">
                        <Coins size={11} />{m.cost}
                      </span>
                    </button>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </header>

      {/* ── Messages ── */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto pt-16 pb-40 px-4"
        onClick={() => pickerOpen && setPickerOpen(false)}
      >
        <div className="max-w-md mx-auto">
          {messages.length === 0 ? (
            <div className="pt-10 flex flex-col items-center text-center">
              <div className="w-16 h-16 rounded-3xl bg-gradient-to-br from-brand-primary to-brand-cyan grid place-items-center shadow-lg shadow-brand-primary/30 mb-5">
                <Sparkles size={30} className="text-white" />
              </div>
              <h1 className="text-2xl font-extrabold text-white mb-1">
                {uz ? `Salom, ${displayName}!` : `Привет, ${displayName}!`}
              </h1>
              <p className="text-sm text-white/50 mb-8">
                {uz ? "Nima haqida gaplashamiz?" : "О чём поговорим?"}
              </p>
              <div className="w-full space-y-2">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="w-full glass-panel p-3.5 text-left text-sm text-white/80 hover:bg-white/5 transition active:scale-[0.99]"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-3 pt-2">
              {messages.map((m, i) => (
                <MessageBubble key={i} role={m.role} content={m.content} pending={m.pending} />
              ))}
            </div>
          )}

          {error && (
            <div className="mt-3 p-3 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-start gap-2 text-red-300">
              <AlertCircle size={16} className="shrink-0 mt-0.5" />
              <p className="text-sm">{error}</p>
            </div>
          )}
        </div>
      </div>

      {/* ── Input bar (sits above the bottom nav) ── */}
      <div className="fixed bottom-16 left-0 right-0 z-40 bg-brand-900/85 backdrop-blur-xl border-t border-white/10 pb-2 pt-2">
        <div className="max-w-md mx-auto px-3 flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(input); }
            }}
            rows={1}
            placeholder={uz ? "Xabar yozing…" : "Напишите сообщение…"}
            className="flex-1 resize-none max-h-32 bg-brand-800/80 border border-white/10 rounded-2xl text-white placeholder-white/35 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary/50 transition"
          />
          <button
            onClick={() => void send(input)}
            disabled={sending || !input.trim()}
            aria-label={uz ? "Yuborish" : "Отправить"}
            className="w-11 h-11 shrink-0 grid place-items-center rounded-2xl bg-gradient-to-br from-brand-primary to-brand-cyan text-white shadow-lg shadow-brand-primary/30 disabled:opacity-40 disabled:shadow-none active:scale-95 transition"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </main>
  );
}

function MessageBubble({ role, content, pending }: { role: "user" | "assistant"; content: string; pending?: boolean }) {
  const isUser = role === "user";
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex ${isUser ? "justify-end" : "justify-start"}`}
    >
      <div
        className={`max-w-[85%] px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap break-words ${
          isUser
            ? "bg-gradient-to-br from-brand-primary to-brand-primary/80 text-white rounded-2xl rounded-br-md"
            : "glass-panel text-white/90 rounded-2xl rounded-bl-md"
        }`}
      >
        {pending ? <TypingDots /> : content}
      </div>
    </motion.div>
  );
}

function TypingDots() {
  return (
    <span className="inline-flex items-center gap-1 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-white/60 animate-bounce"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </span>
  );
}

"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send, Sparkles, ChevronDown, Check, Coins, Brain, Plus, AlertCircle,
  MessageSquare, ImageIcon, Video, Loader2, Clock, X, Paperclip,
} from "lucide-react";
import { useMiniAppUser } from "@/lib/use-miniapp-user";
import {
  api, type ChatModelInfo, type MediaTier, type ChatConversation, ApiError,
} from "@/lib/api";

type MediaKind = "image" | "video";
type Mode = "text" | MediaKind;

type UiMessage = {
  role: "user" | "assistant";
  content: string;
  pending?: boolean;
  pendingKind?: MediaKind;
  media?: { kind: MediaKind; url: string };
  isError?: boolean;
};

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

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export default function ChatPage() {
  const { telegramUser: tgUser, backendUser, language, syncUser } = useMiniAppUser();
  const uz = language === "uz";

  // Text models
  const [models, setModels] = useState<ChatModelInfo[]>([]);
  const [modelId, setModelId] = useState<string>("");

  // Media tiers
  const [tiers, setTiers] = useState<{ image: MediaTier[]; video: MediaTier[] } | null>(null);
  const [imageTierKey, setImageTierKey] = useState<string>("");
  const [videoTierKey, setVideoTierKey] = useState<string>("");

  const [mode, setMode] = useState<Mode>("text");
  const [pickerOpen, setPickerOpen] = useState(false);

  // Conversation history
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);

  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  // Attached reference photo (image-to-image / image-to-video)
  const [attachPreview, setAttachPreview] = useState<string | null>(null);
  const [attachUrl, setAttachUrl] = useState<string | null>(null);
  const [attachUploading, setAttachUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const scrollRef = useRef<HTMLDivElement>(null);
  const credits = backendUser?.credits_balance ?? 0;

  const activeModel = models.find((m) => m.id === modelId);
  const activeTierKey = mode === "image" ? imageTierKey : videoTierKey;
  const activeTier =
    mode !== "text" && tiers ? tiers[mode].find((t) => t.key === activeTierKey) : undefined;

  // Load text models on mount
  useEffect(() => {
    api.getChatModels()
      .then((res) => {
        setModels(res.models);
        if (res.models.length) setModelId((prev) => prev || res.models[0].id);
      })
      .catch(() => setError(uz ? "Modellarni yuklab bo'lmadi" : "Не удалось загрузить модели"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Lazily load media tiers the first time a media mode is opened
  useEffect(() => {
    if (mode === "text" || tiers) return;
    api.getGenerateOptions()
      .then((res) => {
        setTiers(res.tiers);
        if (res.tiers.image.length) setImageTierKey((p) => p || res.tiers.image[0].key);
        if (res.tiers.video.length) setVideoTierKey((p) => p || res.tiers.video[0].key);
      })
      .catch(() => setError(uz ? "Rejimlarni yuklab bo'lmadi" : "Не удалось загрузить режимы"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const refreshConversations = useCallback(() => {
    const tid = backendUser?.telegram_user_id;
    if (!tid) return;
    api.getChatConversations(tid).then((res) => setConversations(res.conversations)).catch(() => {});
  }, [backendUser?.telegram_user_id]);

  const loadConversation = useCallback(
    async (convId: number) => {
      const tid = backendUser?.telegram_user_id;
      if (!tid) return;
      try {
        const res = await api.getChatMessages(tid, convId);
        const msgs: UiMessage[] = res.messages
          .filter((m) => m.role === "user" || m.role === "assistant")
          .map((m) => ({ role: m.role as "user" | "assistant", content: m.content }));
        setMessages(msgs);
        setConversationId(convId);
        setMode("text");
        setHistoryOpen(false);
      } catch {
        /* ignore — leave current view */
      }
    },
    [backendUser?.telegram_user_id],
  );

  // Load conversation list once, and auto-restore the most recent chat so the
  // user continues where they left off (like Suzma). "New chat" starts fresh.
  useEffect(() => {
    const tid = backendUser?.telegram_user_id;
    if (!tid || historyLoaded) return;
    setHistoryLoaded(true);
    api.getChatConversations(tid)
      .then((res) => {
        setConversations(res.conversations);
        if (res.conversations.length && messages.length === 0) {
          void loadConversation(res.conversations[0].id);
        }
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [backendUser?.telegram_user_id]);

  // ── Text chat ──
  const sendText = useCallback(
    async (text: string) => {
      if (!modelId || !backendUser?.telegram_user_id) return;
      setMessages((prev) => [
        ...prev,
        { role: "user", content: text },
        { role: "assistant", content: "", pending: true },
      ]);
      try {
        const res = await api.sendChat({
          telegram_user_id: backendUser.telegram_user_id,
          model_id: modelId,
          message: text,
          conversation_id: conversationId,
        });
        const wasNew = conversationId === null;
        setConversationId(res.conversation_id);
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = { role: "assistant", content: res.reply };
          return next;
        });
        void syncUser();
        if (wasNew) refreshConversations();
      } catch (e) {
        setMessages((prev) => prev.slice(0, -1));
        setError(e instanceof ApiError ? e.message : uz ? "Xatolik" : "Ошибка");
      }
    },
    [modelId, backendUser?.telegram_user_id, conversationId, syncUser, uz, refreshConversations],
  );

  // ── Image / video generation ──
  const sendGeneration = useCallback(
    async (text: string, kind: MediaKind, tierKey: string, sourceImageUrl?: string | null) => {
      if (!tierKey || !backendUser?.telegram_user_id) return;
      const newMsgs: UiMessage[] = [];
      if (sourceImageUrl) newMsgs.push({ role: "user", content: "", media: { kind: "image", url: sourceImageUrl } });
      newMsgs.push({ role: "user", content: text });
      newMsgs.push({ role: "assistant", content: "", pending: true, pendingKind: kind });
      setMessages((prev) => [...prev, ...newMsgs]);
      try {
        const job = await api.createGeneration({
          telegram_user_id: backendUser.telegram_user_id,
          quality_key: tierKey,
          prompt: text,
          source_image_url: sourceImageUrl ?? null,
        });
        void syncUser(); // credits are reserved on creation

        // Poll until the worker finishes (video can take a few minutes)
        let done = job;
        for (let i = 0; i < 120; i++) {
          if (done.status === "completed" || done.status === "failed") break;
          await sleep(3000);
          done = await api.getJob(job.id);
        }

        setMessages((prev) => {
          const next = [...prev];
          if (done.status === "completed" && done.result_url) {
            next[next.length - 1] = { role: "assistant", content: "", media: { kind, url: done.result_url } };
          } else if (done.status === "failed") {
            next[next.length - 1] = {
              role: "assistant",
              content: (uz ? "Generatsiya xato: " : "Генерация не удалась: ") + (done.error_message || "—") + (uz ? " · Kreditlar qaytarildi" : " · Кредиты возвращены"),
              isError: true,
            };
          } else {
            next[next.length - 1] = {
              role: "assistant",
              content: uz
                ? "Hali tayyorlanmoqda — «Ishlar» bo'limida ko'ring."
                : "Всё ещё генерируется — результат появится в разделе «Работы».",
            };
          }
          return next;
        });
        void syncUser();
      } catch (e) {
        setMessages((prev) => prev.slice(0, -1));
        setError(e instanceof ApiError ? e.message : uz ? "Xatolik" : "Ошибка");
      }
    },
    [backendUser?.telegram_user_id, syncUser, uz],
  );

  const send = useCallback(
    async (raw: string) => {
      const text = raw.trim();
      if (!text || sending || attachUploading) return;
      setError("");
      setInput("");
      const srcUrl = attachUrl;
      setAttachPreview(null);
      setAttachUrl(null);
      setSending(true);
      try {
        if (mode === "text") await sendText(text);
        else await sendGeneration(text, mode, mode === "image" ? imageTierKey : videoTierKey, srcUrl);
      } finally {
        setSending(false);
      }
    },
    [sending, attachUploading, attachUrl, mode, imageTierKey, videoTierKey, sendText, sendGeneration],
  );

  async function onFilePicked(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-picking the same file
    if (!file) return;
    setError("");
    setAttachPreview(URL.createObjectURL(file));
    setAttachUploading(true);
    try {
      const res = await api.uploadImage(file);
      setAttachUrl(res.url);
    } catch {
      setError(uz ? "Rasmni yuklab bo'lmadi" : "Не удалось загрузить фото");
      setAttachPreview(null);
    } finally {
      setAttachUploading(false);
    }
  }

  function removeAttach() {
    setAttachPreview(null);
    setAttachUrl(null);
  }

  function newChat() {
    setMessages([]);
    setConversationId(null);
    setError("");
    removeAttach();
  }

  const displayName = tgUser?.first_name || (uz ? "Ijodkor" : "Творец");
  const suggestions = uz ? SUGGESTIONS_UZ : SUGGESTIONS_RU;

  const modes: { id: Mode; icon: typeof MessageSquare; labelRu: string; labelUz: string }[] = [
    { id: "text", icon: MessageSquare, labelRu: "Текст", labelUz: "Matn" },
    { id: "image", icon: ImageIcon, labelRu: "Фото", labelUz: "Rasm" },
    { id: "video", icon: Video, labelRu: "Видео", labelUz: "Video" },
  ];

  const pickerLabel =
    mode === "text"
      ? activeModel?.label ?? (uz ? "Модель" : "Модель")
      : activeTier
        ? `${activeTier.emoji} ${activeTier.label}`
        : uz ? "Rejim" : "Режим";

  const placeholder =
    mode === "text"
      ? uz ? "Xabar yozing…" : "Напишите сообщение…"
      : mode === "image"
        ? uz ? "Rasmni tasvirlab bering…" : "Опишите изображение…"
        : uz ? "Videoni tasvirlab bering…" : "Опишите видео…";

  return (
    <main className="min-h-screen flex flex-col">
      {/* ── Header: model/tier selector + balance ── */}
      <header className="fixed top-0 left-0 right-0 z-40 bg-brand-900/80 backdrop-blur-xl border-b border-white/10">
        <div className="max-w-md mx-auto px-4 h-14 flex items-center justify-between gap-3">
          <button
            onClick={() => setPickerOpen((v) => !v)}
            className="flex items-center gap-2 min-w-0 px-3 py-2 rounded-xl bg-white/5 border border-white/10 active:scale-95 transition"
          >
            <Sparkles size={16} className="text-brand-cyan shrink-0" />
            <span className="text-sm font-semibold text-white truncate">{pickerLabel}</span>
            {mode !== "text" && activeTier && (
              <span className="text-[11px] font-bold text-brand-accent flex items-center gap-0.5 shrink-0">
                <Coins size={10} />{activeTier.cost}
              </span>
            )}
            <ChevronDown size={15} className={`text-white/50 shrink-0 transition ${pickerOpen ? "rotate-180" : ""}`} />
          </button>

          <div className="flex items-center gap-2 shrink-0">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-brand-primary/15 border border-brand-primary/25">
              <Coins size={14} className="text-brand-accent" />
              <span className="text-sm font-bold text-white tabular-nums">{credits}</span>
            </div>
            <button
              onClick={() => { setHistoryOpen((v) => !v); setPickerOpen(false); }}
              aria-label={uz ? "Tarix" : "История"}
              className="w-9 h-9 grid place-items-center rounded-xl bg-white/5 border border-white/10 active:scale-95 transition"
            >
              <Clock size={17} className="text-white/80" />
            </button>
            <button
              onClick={newChat}
              aria-label={uz ? "Yangi suhbat" : "Новый чат"}
              className="w-9 h-9 grid place-items-center rounded-xl bg-white/5 border border-white/10 active:scale-95 transition"
            >
              <Plus size={18} className="text-white/80" />
            </button>
          </div>
        </div>

        {/* History dropdown */}
        <AnimatePresence>
          {historyOpen && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="max-w-md mx-auto px-4 pb-3"
            >
              <div className="glass-card p-1.5 max-h-[60vh] overflow-y-auto">
                <div className="flex items-center justify-between px-3 py-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-white/40">
                    {uz ? "Suhbatlar" : "История чатов"}
                  </span>
                  <button onClick={() => setHistoryOpen(false)} className="text-white/40 hover:text-white/70">
                    <X size={15} />
                  </button>
                </div>
                {conversations.length === 0 ? (
                  <p className="px-3 py-4 text-sm text-white/40 text-center">
                    {uz ? "Hali suhbatlar yo'q" : "Пока нет диалогов"}
                  </p>
                ) : (
                  conversations.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => loadConversation(c.id)}
                      className={`w-full flex items-center gap-3 p-3 rounded-2xl text-left transition ${
                        c.id === conversationId ? "bg-brand-primary/20" : "hover:bg-white/5"
                      }`}
                    >
                      <MessageSquare size={15} className="text-brand-cyan shrink-0" />
                      <span className="text-sm text-white truncate flex-1">
                        {c.title || (uz ? "Suhbat" : "Диалог")} #{c.id}
                      </span>
                    </button>
                  ))
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Picker dropdown: text models OR media tiers */}
        <AnimatePresence>
          {pickerOpen && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="max-w-md mx-auto px-4 pb-3"
            >
              <div className="glass-card p-1.5 max-h-[60vh] overflow-y-auto">
                {mode === "text"
                  ? models.map((m) => (
                      <PickerRow
                        key={m.id}
                        active={m.id === modelId}
                        icon={m.reasoning ? <Brain size={16} className="text-white" /> : <Sparkles size={16} className="text-white" />}
                        title={m.label}
                        subtitle={m.description}
                        cost={m.cost}
                        onClick={() => { setModelId(m.id); setPickerOpen(false); }}
                      />
                    ))
                  : (tiers?.[mode] ?? []).map((t) => (
                      <PickerRow
                        key={t.key}
                        active={t.key === activeTierKey}
                        icon={<span className="text-base leading-none">{t.emoji}</span>}
                        title={t.label}
                        subtitle={t.note}
                        cost={t.cost}
                        onClick={() => {
                          if (mode === "image") setImageTierKey(t.key); else setVideoTierKey(t.key);
                          setPickerOpen(false);
                        }}
                      />
                    ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </header>

      {/* ── Messages ── */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto pt-16 pb-48 px-4"
        onClick={() => { if (pickerOpen) setPickerOpen(false); if (historyOpen) setHistoryOpen(false); }}
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
                {mode === "text"
                  ? uz ? "Nima haqida gaplashamiz?" : "О чём поговорим?"
                  : mode === "image"
                    ? uz ? "Qanday rasm yarataylik?" : "Какое изображение создать?"
                    : uz ? "Qanday video yarataylik?" : "Какое видео создать?"}
              </p>
              {mode === "text" && (
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
              )}
            </div>
          ) : (
            <div className="space-y-3 pt-2">
              {messages.map((m, i) => (
                <MessageBubble key={i} msg={m} uz={uz} />
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
        <div className="max-w-md mx-auto px-3 space-y-2">
          {/* Mode toggle */}
          <div className="flex items-center gap-1.5">
            {modes.map(({ id, icon: Icon, labelRu, labelUz }) => {
              const active = mode === id;
              return (
                <button
                  key={id}
                  onClick={() => { setMode(id); setPickerOpen(false); }}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition ${
                    active
                      ? "bg-gradient-to-r from-brand-primary to-brand-cyan text-white"
                      : "bg-white/5 text-white/50 border border-white/10"
                  }`}
                >
                  <Icon size={13} />
                  {uz ? labelUz : labelRu}
                </button>
              );
            })}
          </div>

          {/* Attached reference photo chip (media modes) */}
          {attachPreview && (
            <div className="flex items-center gap-2 px-2 py-1.5 rounded-xl bg-white/5 border border-white/10 w-fit">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={attachPreview} alt="attach" className="w-10 h-10 rounded-lg object-cover" />
              <span className="text-xs text-white/60">
                {attachUploading
                  ? (uz ? "Yuklanmoqda…" : "Загрузка…")
                  : (uz ? "Foto biriktirildi" : "Фото прикреплено")}
              </span>
              {attachUploading && <Loader2 size={13} className="animate-spin text-brand-cyan" />}
              <button onClick={removeAttach} aria-label={uz ? "O'chirish" : "Убрать"} className="text-white/40 hover:text-white/80">
                <X size={14} />
              </button>
            </div>
          )}

          <div className="flex items-end gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={onFilePicked}
              className="hidden"
            />
            {mode !== "text" && (
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={sending}
                aria-label={uz ? "Foto biriktirish" : "Прикрепить фото"}
                className="w-11 h-11 shrink-0 grid place-items-center rounded-2xl bg-white/5 border border-white/10 text-white/70 disabled:opacity-40 active:scale-95 transition"
              >
                <Paperclip size={18} />
              </button>
            )}
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(input); }
              }}
              rows={1}
              placeholder={placeholder}
              disabled={sending}
              className="flex-1 resize-none max-h-32 bg-brand-800/80 border border-white/10 rounded-2xl text-white placeholder-white/35 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary/50 transition disabled:opacity-60"
            />
            <button
              onClick={() => void send(input)}
              disabled={sending || attachUploading || !input.trim()}
              aria-label={uz ? "Yuborish" : "Отправить"}
              className="w-11 h-11 shrink-0 grid place-items-center rounded-2xl bg-gradient-to-br from-brand-primary to-brand-cyan text-white shadow-lg shadow-brand-primary/30 disabled:opacity-40 disabled:shadow-none active:scale-95 transition"
            >
              {sending ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}

function PickerRow({
  active, icon, title, subtitle, cost, onClick,
}: {
  active: boolean; icon: React.ReactNode; title: string; subtitle: string; cost: number; onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-start gap-3 p-3 rounded-2xl text-left transition ${active ? "bg-brand-primary/20" : "hover:bg-white/5"}`}
    >
      <div className="w-8 h-8 shrink-0 rounded-lg bg-gradient-to-br from-brand-primary to-brand-cyan grid place-items-center">
        {icon}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-white">{title}</span>
          {active && <Check size={14} className="text-brand-cyan shrink-0" />}
        </div>
        {subtitle && <p className="text-xs text-white/45 leading-snug mt-0.5">{subtitle}</p>}
      </div>
      <span className="shrink-0 text-[11px] font-bold text-brand-accent flex items-center gap-1 mt-0.5">
        <Coins size={11} />{cost}
      </span>
    </button>
  );
}

function MessageBubble({ msg, uz }: { msg: UiMessage; uz: boolean }) {
  const isUser = msg.role === "user";

  // Media bubble — assistant result OR the user's attached reference photo
  if (msg.media) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className={`flex ${isUser ? "justify-end" : "justify-start"}`}
      >
        <div
          className={`max-w-[70%] overflow-hidden p-1 rounded-2xl ${
            isUser ? "bg-brand-primary/25 rounded-br-md" : "glass-panel rounded-bl-md"
          }`}
        >
          {msg.media.kind === "image" ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={msg.media.url} alt={isUser ? "attached" : "result"} className="rounded-xl w-full h-auto" />
          ) : (
            <video src={msg.media.url} controls playsInline className="rounded-xl w-full h-auto" />
          )}
        </div>
      </motion.div>
    );
  }

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
            : msg.isError
              ? "bg-red-500/10 border border-red-500/20 text-red-300 rounded-2xl rounded-bl-md"
              : "glass-panel text-white/90 rounded-2xl rounded-bl-md"
        }`}
      >
        {msg.pending
          ? msg.pendingKind
            ? <GeneratingLabel kind={msg.pendingKind} uz={uz} />
            : <TypingDots />
          : msg.content}
      </div>
    </motion.div>
  );
}

function GeneratingLabel({ kind, uz }: { kind: MediaKind; uz: boolean }) {
  const label =
    kind === "image"
      ? uz ? "Rasm tayyorlanmoqda…" : "Генерирую изображение…"
      : uz ? "Video tayyorlanmoqda…" : "Генерирую видео…";
  return (
    <span className="inline-flex items-center gap-2 py-0.5 text-white/70">
      <Loader2 size={15} className="animate-spin text-brand-cyan" />
      {label}
    </span>
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

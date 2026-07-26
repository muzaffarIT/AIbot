"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send, Sparkles, ChevronDown, Check, Coins, Brain, Plus, AlertCircle,
  MessageSquare, ImageIcon, Video, Loader2, Clock, X, Paperclip,
  Download, ExternalLink, Mic, Square,
} from "lucide-react";
import { useMiniAppUser } from "@/lib/use-miniapp-user";
import {
  api, type ChatModelInfo, type MediaTier, type ChatConversation, ApiError,
} from "@/lib/api";

type MediaKind = "image" | "video";
type Mode = "text" | MediaKind;

type UiMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  pending?: boolean;
  pendingKind?: MediaKind;
  media?: { kind: MediaKind; url: string };
  isError?: boolean;
};

let msgSeq = 0;
const nextId = () => `m${++msgSeq}`;

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

/** Save a result. Long-press "save" is unreliable in the Telegram WebView,
 *  so prefer Telegram's own downloadFile (Bot API 8+), then a blob download,
 *  then simply opening the file. */
async function downloadMedia(url: string, kind: MediaKind) {
  const name = `harf-ai-${Date.now()}.${kind === "image" ? "jpg" : "mp4"}`;

  const tg = (window as unknown as { Telegram?: { WebApp?: { downloadFile?: (p: { url: string; file_name: string }) => void } } })
    .Telegram?.WebApp;
  if (tg?.downloadFile) {
    tg.downloadFile({ url, file_name: name });
    return;
  }

  try {
    const res = await fetch(url);
    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = objectUrl;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(objectUrl), 10_000);
  } catch {
    // CORS or offline — fall back to opening the file in a new tab
    window.open(url, "_blank", "noopener,noreferrer");
  }
}

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

  // Voice input
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const scrollRef = useRef<HTMLDivElement>(null);
  const credits = backendUser?.credits_balance ?? 0;

  const activeModel = models.find((m) => m.id === modelId);
  const activeTierKey = mode === "image" ? imageTierKey : videoTierKey;
  const activeTier =
    mode !== "text" && tiers ? tiers[mode].find((t) => t.key === activeTierKey) : undefined;

  // Load text models — refetched when the UI language changes so model
  // descriptions come back localized.
  useEffect(() => {
    api.getChatModels(language)
      .then((res) => {
        setModels(res.models);
        if (res.models.length) setModelId((prev) => prev || res.models[0].id);
      })
      .catch(() => setError(uz ? "Modellarni yuklab bo'lmadi" : "Не удалось загрузить модели"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language]);

  // Media tiers — also language-aware (notes like "5 сек" / "5 soniya").
  useEffect(() => {
    api.getGenerateOptions(language)
      .then((res) => {
        setTiers(res.tiers);
        if (res.tiers.image.length) setImageTierKey((p) => p || res.tiers.image[0].key);
        if (res.tiers.video.length) setVideoTierKey((p) => p || res.tiers.video[0].key);
      })
      .catch(() => setError(uz ? "Rejimlarni yuklab bo'lmadi" : "Не удалось загрузить режимы"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language]);

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
          .map((m) => ({ id: nextId(), role: m.role as "user" | "assistant", content: m.content }));
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
      const pendingId = nextId();
      setMessages((prev) => [
        ...prev,
        { id: nextId(), role: "user", content: text },
        { id: pendingId, role: "assistant", content: "", pending: true },
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
        setMessages((prev) =>
          prev.map((m) => (m.id === pendingId ? { ...m, pending: false, content: res.reply } : m)),
        );
        void syncUser();
        if (wasNew) refreshConversations();
      } catch (e) {
        setMessages((prev) => prev.filter((m) => m.id !== pendingId));
        setError(e instanceof ApiError ? e.message : uz ? "Xatolik" : "Ошибка");
      }
    },
    [modelId, backendUser?.telegram_user_id, conversationId, syncUser, uz, refreshConversations],
  );

  // ── Image / video generation ──
  const sendGeneration = useCallback(
    async (text: string, kind: MediaKind, tierKey: string, sourceImageUrl?: string | null) => {
      if (!tierKey || !backendUser?.telegram_user_id) return;
      const pendingId = nextId();
      const newMsgs: UiMessage[] = [];
      if (sourceImageUrl) {
        newMsgs.push({ id: nextId(), role: "user", content: "", media: { kind: "image", url: sourceImageUrl } });
      }
      newMsgs.push({ id: nextId(), role: "user", content: text });
      newMsgs.push({ id: pendingId, role: "assistant", content: "", pending: true, pendingKind: kind });
      setMessages((prev) => [...prev, ...newMsgs]);

      const patch = (fields: Partial<UiMessage>) =>
        setMessages((prev) => prev.map((m) => (m.id === pendingId ? { ...m, ...fields } : m)));

      try {
        const job = await api.createGeneration({
          telegram_user_id: backendUser.telegram_user_id,
          quality_key: tierKey,
          prompt: text,
          source_image_url: sourceImageUrl ?? null,
        });
        void syncUser(); // credits are reserved on creation

        // Poll until the worker finishes (video can take a few minutes).
        // This runs unblocked, so the user can keep chatting meanwhile.
        let done = job;
        for (let i = 0; i < 120; i++) {
          if (done.status === "completed" || done.status === "failed") break;
          await sleep(3000);
          try {
            done = await api.getJob(job.id);
          } catch {
            /* transient network hiccup — keep polling */
          }
        }

        if (done.status === "completed" && done.result_url) {
          patch({ pending: false, pendingKind: undefined, media: { kind, url: done.result_url } });
        } else if (done.status === "failed") {
          patch({
            pending: false,
            pendingKind: undefined,
            isError: true,
            content:
              (uz ? "Generatsiya xato: " : "Генерация не удалась: ") +
              (done.error_message || "—") +
              (uz ? " · Kreditlar qaytarildi" : " · Кредиты возвращены"),
          });
        } else {
          patch({
            pending: false,
            pendingKind: undefined,
            content: uz
              ? "Hali tayyorlanmoqda — «Ishlar» bo'limida ko'ring."
              : "Всё ещё генерируется — результат появится в разделе «Работы».",
          });
        }
        void syncUser();
      } catch (e) {
        setMessages((prev) => prev.filter((m) => m.id !== pendingId));
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

      if (mode !== "text") {
        // Generation can take minutes — fire it off and leave the composer
        // usable. Progress lives in its own pending bubble.
        void sendGeneration(text, mode, mode === "image" ? imageTierKey : videoTierKey, srcUrl);
        return;
      }

      setSending(true);
      try {
        await sendText(text);
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
    // A photo only makes sense for generation — jump out of plain text mode
    // so the prompt is used as an image edit instruction.
    if (mode === "text") setMode("image");
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

  // ── Voice input: record → upload → transcribe → drop into the composer ──
  async function startRecording() {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      chunksRef.current = [];
      rec.ondataavailable = (ev) => { if (ev.data.size) chunksRef.current.push(ev.data); };
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: rec.mimeType || "audio/webm" });
        if (!blob.size) return;
        setTranscribing(true);
        try {
          const { url } = await api.uploadAudio(blob);
          const { text } = await api.transcribe(url, language);
          setInput((prev) => (prev ? `${prev} ${text}` : text));
        } catch (e) {
          setError(
            e instanceof ApiError
              ? e.message
              : uz ? "Ovozni aniqlab bo'lmadi" : "Не удалось распознать голос",
          );
        } finally {
          setTranscribing(false);
        }
      };
      rec.start();
      recorderRef.current = rec;
      setRecording(true);
    } catch {
      setError(uz ? "Mikrofonga ruxsat berilmadi" : "Нет доступа к микрофону");
    }
  }

  function stopRecording() {
    recorderRef.current?.stop();
    recorderRef.current = null;
    setRecording(false);
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
      ? activeModel?.label ?? (uz ? "Model" : "Модель")
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
              {messages.map((m) => (
                <MessageBubble key={m.id} msg={m} uz={uz} />
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
                  onClick={() => { setMode(id); setPickerOpen(false); setHistoryOpen(false); }}
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
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={sending}
              aria-label={uz ? "Foto biriktirish" : "Прикрепить фото"}
              className="w-11 h-11 shrink-0 grid place-items-center rounded-2xl bg-white/5 border border-white/10 text-white/70 disabled:opacity-40 active:scale-95 transition"
            >
              <Paperclip size={18} />
            </button>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(input); }
              }}
              rows={1}
              placeholder={placeholder}
              disabled={sending}
              /* text-base (16px) is required — anything smaller makes iOS
                 WebView auto-zoom the whole page when the field is focused. */
              className="flex-1 resize-none max-h-32 bg-brand-800/80 border border-white/10 rounded-2xl text-white placeholder-white/35 px-4 py-3 text-base focus:outline-none focus:ring-2 focus:ring-brand-primary/50 transition disabled:opacity-60"
            />
            {/* Mic when there's nothing to send, otherwise the send button */}
            {!input.trim() && !sending ? (
              <button
                onClick={() => (recording ? stopRecording() : void startRecording())}
                disabled={transcribing}
                aria-label={
                  recording
                    ? (uz ? "To'xtatish" : "Остановить")
                    : (uz ? "Ovozli xabar" : "Голосовое сообщение")
                }
                className={`w-11 h-11 shrink-0 grid place-items-center rounded-2xl border transition active:scale-95 disabled:opacity-40 ${
                  recording
                    ? "bg-red-500/20 border-red-500/40 text-red-300 animate-pulse"
                    : "bg-white/5 border-white/10 text-white/70"
                }`}
              >
                {transcribing
                  ? <Loader2 size={18} className="animate-spin" />
                  : recording ? <Square size={16} /> : <Mic size={18} />}
              </button>
            ) : (
              <button
                onClick={() => void send(input)}
                disabled={sending || attachUploading || !input.trim()}
                aria-label={uz ? "Yuborish" : "Отправить"}
                className="w-11 h-11 shrink-0 grid place-items-center rounded-2xl bg-gradient-to-br from-brand-primary to-brand-cyan text-white shadow-lg shadow-brand-primary/30 disabled:opacity-40 disabled:shadow-none active:scale-95 transition"
              >
                {sending ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
              </button>
            )}
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
    const media = msg.media;
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
          {media.kind === "image" ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={media.url} alt={isUser ? "attached" : "result"} className="rounded-xl w-full h-auto" />
          ) : (
            <video src={media.url} controls playsInline className="rounded-xl w-full h-auto" />
          )}
          {/* Saving via long-press is unreliable inside the Telegram WebView,
              so results get explicit Save / Open actions. */}
          {!isUser && (
            <div className="flex items-center gap-1.5 px-1.5 pt-1.5 pb-0.5">
              <button
                onClick={() => downloadMedia(media.url, media.kind)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/10 text-xs font-semibold text-white/85 active:scale-95 transition"
              >
                <Download size={13} />
                {uz ? "Saqlash" : "Сохранить"}
              </button>
              <a
                href={media.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/10 text-xs font-semibold text-white/85 active:scale-95 transition"
              >
                <ExternalLink size={13} />
                {uz ? "Ochish" : "Открыть"}
              </a>
            </div>
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
          : (!isUser && !msg.isError)
            ? <MarkdownText text={msg.content} />
            : msg.content}
      </div>
    </motion.div>
  );
}

// ── Minimal, safe markdown renderer (no deps, no HTML injection) ──
// Handles fenced code blocks, plus inline **bold**, *italic* and `code`.
// Everything else stays as-is; the bubble's whitespace-pre-wrap keeps
// line breaks and list layout intact.
function renderInline(text: string, keyBase: string): React.ReactNode[] {
  const tokens = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*\n]+\*)/g);
  return tokens.map((tok, i) => {
    const key = `${keyBase}-${i}`;
    if (tok.length > 4 && tok.startsWith("**") && tok.endsWith("**")) {
      return <strong key={key} className="font-semibold text-white">{tok.slice(2, -2)}</strong>;
    }
    if (tok.length > 2 && tok.startsWith("`") && tok.endsWith("`")) {
      return <code key={key} className="px-1 py-0.5 rounded bg-white/10 text-[0.85em] font-mono">{tok.slice(1, -1)}</code>;
    }
    if (tok.length > 2 && tok.startsWith("*") && tok.endsWith("*")) {
      return <em key={key}>{tok.slice(1, -1)}</em>;
    }
    return tok;
  });
}

function MarkdownText({ text }: { text: string }) {
  const parts = text.split("```");
  return (
    <>
      {parts.map((part, i) =>
        i % 2 === 1 ? (
          <pre key={i} className="my-1.5 p-2.5 rounded-lg bg-black/30 overflow-x-auto text-xs font-mono text-white/90 whitespace-pre">
            <code>{part.replace(/^[\w-]*\n/, "")}</code>
          </pre>
        ) : (
          <span key={i}>{renderInline(part, String(i))}</span>
        )
      )}
    </>
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

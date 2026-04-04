// ─── Types ────────────────────────────────────────────────────────────────────

export type BackendUser = {
  id: number;
  telegram_user_id: number;
  username?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  language_code: string;
  credits_balance?: number;
  referral_count?: number;
  daily_streak?: number;
  created_at?: string | null;
};

export type BalanceResponse = {
  user_id: number;
  telegram_user_id: number;
  credits_balance: number;
};

export type BalanceTransaction = {
  id: number;
  transaction_type: string;
  amount: number;
  balance_before: number;
  balance_after: number;
  reference_type?: string | null;
  reference_id?: string | null;
  comment?: string | null;
  created_at?: string | null;
};

export type BalanceHistoryResponse = BalanceResponse & {
  transactions: BalanceTransaction[];
};

export type Plan = {
  id: number;
  code: string;
  name: string;
  description?: string | null;
  price: number;
  currency: string;
  credits_amount: number;
  duration_days?: number | null;
  is_active?: boolean;
};

export type OrderSummary = {
  id: number;
  order_number: string;
  user_id: number;
  plan_id: number;
  plan_name?: string | null;
  plan_code?: string | null;
  amount: number;
  currency: string;
  status: string;
  payment_method?: string | null;
  created_at?: string | null;
};

export type OrdersResponse = {
  user_id: number;
  telegram_user_id: number;
  orders: OrderSummary[];
};

export type GenerationProvider = "nano_banana" | "kling" | "veo";

export type GenerationJob = {
  id: number;
  user_id: number;
  provider: GenerationProvider;
  prompt: string;
  source_image_url?: string | null;
  status: string;
  credits_reserved: number;
  external_job_id?: string | null;
  result_url?: string | null;
  result_payload?: string | null;
  error_message?: string | null;
  completed_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type GenerationJobsResponse = {
  telegram_user_id: number;
  jobs: GenerationJob[];
};

export type PaymentResponse = {
  id: number;
  order_id: number;
  provider: string;
  method: string;
  amount: number;
  currency: string;
  status: string;
  paid_at?: string | null;
  created_at?: string | null;
  order_status?: string;
  credited_amount?: number;
  current_balance?: number;
  plan_code?: string;
  plan_name?: string;
};

export type ManualPaymentResult = {
  payment_id: number;
  order_id: number;
  order_number: string;
  amount: number;
  currency: string;
  credits: number;
  plan_name: string;
  plan_code: string;
  card_number: string;
  card_owner: string;
  visa_card_number: string;
  visa_card_owner: string;
  already_pending: boolean;
};

export type AchievementItem = {
  code: string;
  name: string;
  emoji: string;
  bonus: number;
  earned: boolean;
};

export type ReferralData = {
  referral_code: string;
  referral_count: number;
  referral_earnings: number;
};

// ─── Error class ──────────────────────────────────────────────────────────────

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

// ─── Core request ─────────────────────────────────────────────────────────────

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL?.trim() ?? "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = BACKEND_URL ? `${BACKEND_URL}${path}` : path;

  // Always include TMA auth when available
  let initData = "";
  if (typeof window !== "undefined") {
    initData = window.Telegram?.WebApp?.initData ?? "";
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string> ?? {}),
  };
  if (initData) {
    headers["Authorization"] = `tma ${initData}`;
  }

  const res = await fetch(url, {
    cache: "no-store",
    ...options,
    headers,
  });

  if (!res.ok) {
    let msg = res.statusText || `Request failed: ${res.status}`;
    try {
      const data = (await res.json()) as { detail?: string };
      if (data?.detail) msg = data.detail;
    } catch {}
    throw new ApiError(msg, res.status);
  }

  return res.json() as Promise<T>;
}

// ─── fetchJson (legacy alias, same behaviour) ─────────────────────────────────

export async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  return request<T>(path, options);
}

// ─── Clean api object ─────────────────────────────────────────────────────────

export const api = {
  syncUser: (data: {
    telegram_id: number;
    username?: string | null;
    first_name?: string | null;
    last_name?: string | null;
    language_code?: string | null;
  }) =>
    request<BackendUser>("/api/users/sync", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getProfile: (telegramId: number) =>
    request<BackendUser>(`/api/users/${telegramId}`),

  getAchievements: (telegramId: number) =>
    request<AchievementItem[]>(`/api/users/${telegramId}/achievements`),

  getReferral: (telegramId: number) =>
    request<ReferralData>(`/api/users/${telegramId}/referral`),

  getJobs: (telegramId: number, limit = 20) =>
    request<GenerationJobsResponse>(`/api/jobs/telegram/${telegramId}?limit=${limit}`),

  getPlans: () => request<Plan[]>("/api/plans"),

  getBalanceHistory: (telegramId: number, limit = 20) =>
    request<BalanceHistoryResponse>(
      `/api/balances/telegram/${telegramId}/transactions?limit=${limit}`
    ),

  getOrders: (telegramId: number, limit = 10) =>
    request<OrdersResponse>(`/api/orders/telegram/${telegramId}?limit=${limit}`),

  createManualPayment: (data: { telegram_user_id: number; plan_code: string }) =>
    request<ManualPaymentResult>("/api/payments/create-manual", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  notifyPaid: (paymentId: number) =>
    request<{ status: string; payment_id: number }>(`/api/payments/${paymentId}/notify-paid`, {
      method: "POST",
    }),

  cancelPayment: (paymentId: number) =>
    request<{ status: string; payment_id: number }>(`/api/payments/${paymentId}/cancel`, {
      method: "POST",
    }),
};

// ─── Legacy named exports (used by existing pages) ────────────────────────────

export async function ensureUser(payload: {
  telegram_user_id: number;
  username?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  language_code?: string | null;
}) {
  return request<BackendUser>("/api/users/ensure", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function syncUser(payload: {
  telegram_id: number;
  username?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  language_code?: string | null;
}) {
  return api.syncUser(payload);
}

export async function getUser(telegramUserId: number) {
  return api.getProfile(telegramUserId);
}

export async function updateLanguage(telegramUserId: number, language: string) {
  return request<{ success: boolean; language: string }>("/api/users/language", {
    method: "PATCH",
    body: JSON.stringify({ telegram_user_id: telegramUserId, language }),
  });
}

export async function getBalance(telegramUserId: number) {
  return request<BalanceResponse>(`/api/balances/telegram/${telegramUserId}`);
}

export async function getBalanceHistory(telegramUserId: number, limit = 10) {
  return api.getBalanceHistory(telegramUserId, limit);
}

export async function getPlans() {
  return api.getPlans();
}

export async function getOrders(telegramUserId: number, limit = 10) {
  return api.getOrders(telegramUserId, limit);
}

export async function getJobs(telegramUserId: number, limit = 10) {
  return api.getJobs(telegramUserId, limit);
}

export async function getJob(jobId: number) {
  return request<GenerationJob>(`/api/jobs/${jobId}`);
}

export async function createJob(payload: {
  telegram_user_id: number;
  provider: GenerationProvider;
  quality_key: string;
  prompt: string;
  source_image_url?: string;
  process_now?: boolean;
}) {
  return request<GenerationJob>("/api/jobs/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function createOrder(payload: {
  telegram_user_id: number;
  plan_code: string;
  email?: string | null;
  payment_method?: string | null;
}) {
  return request<OrderSummary>("/api/orders/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function createPayment(payload: {
  order_id: number;
  provider: string;
  method: string;
}) {
  return request<PaymentResponse>("/api/payments/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function confirmPayment(paymentId: number) {
  return request<PaymentResponse>(`/api/payments/${paymentId}/confirm`, {
    method: "POST",
  });
}

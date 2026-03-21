const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || "";

export type BackendUser = {
  id: number;
  telegram_user_id: number;
  username?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  language_code: string;
  credits_balance?: number;
  referral_count?: number;
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

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function readErrorMessage(response: Response) {
  try {
    const data = (await response.json()) as { detail?: string };
    if (data?.detail) {
      return data.detail;
    }
  } catch {
    return response.statusText || `Request failed: ${response.status}`;
  }

  return response.statusText || `Request failed: ${response.status}`;
}

export async function fetchJson<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = BACKEND_URL ? `${BACKEND_URL}${path}` : path;

  const response = await fetch(url, {
    cache: "no-store",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
  });

  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response), response.status);
  }

  return (await response.json()) as T;
}

export async function ensureUser(payload: {
  telegram_user_id: number;
  username?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  language_code?: string | null;
}) {
  return fetchJson<BackendUser>(`/api/users/ensure`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getUser(telegramUserId: number) {
  return fetchJson<BackendUser>(`/api/users/${telegramUserId}`);
}

export async function getBalance(telegramUserId: number) {
  return fetchJson<BalanceResponse>(`/api/balances/telegram/${telegramUserId}`);
}

export async function getBalanceHistory(telegramUserId: number, limit = 10) {
  return fetchJson<BalanceHistoryResponse>(
    `/api/balances/telegram/${telegramUserId}/transactions?limit=${limit}`
  );
}

export async function getPlans() {
  return fetchJson<Plan[]>(`/api/plans`);
}

export async function getOrders(telegramUserId: number, limit = 10) {
  return fetchJson<OrdersResponse>(
    `/api/orders/telegram/${telegramUserId}?limit=${limit}`
  );
}

export async function getJobs(telegramUserId: number, limit = 10) {
  return fetchJson<GenerationJobsResponse>(
    `/api/jobs/telegram/${telegramUserId}?limit=${limit}`
  );
}

export async function getJob(jobId: number) {
  return fetchJson<GenerationJob>(`/api/jobs/${jobId}`);
}

export async function createJob(payload: {
  telegram_user_id: number;
  provider: GenerationProvider;
  prompt: string;
  source_image_url?: string;
  process_now?: boolean;
}) {
  return fetchJson<GenerationJob>(`/api/jobs/`, {
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
  return fetchJson<OrderSummary>(`/api/orders/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function createPayment(payload: {
  order_id: number;
  provider: string;
  method: string;
}) {
  return fetchJson<PaymentResponse>(`/api/payments/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function confirmPayment(paymentId: number) {
  return fetchJson<PaymentResponse>(`/api/payments/${paymentId}/confirm`, {
    method: "POST",
  });
}

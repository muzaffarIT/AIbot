"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createOrder, createPayment, getPlans, type Plan } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { t } from "@/lib/miniapp-i18n";
import { useMiniAppUser } from "@/lib/use-miniapp-user";

export default function PlansPage() {
  const router = useRouter();
  const { backendUser, telegramUser, language } = useMiniAppUser();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [error, setError] = useState("");
  const [loadingCode, setLoadingCode] = useState<string>("");

  useEffect(() => {
    async function load() {
      try {
        const data = await getPlans();
        setPlans(data);
      } catch {
        setError(t(language, "plans.failedLoad"));
      }
    }

    void load();
  }, [language]);

  async function handleBuy(plan: Plan) {
    if (!backendUser?.telegram_user_id) {
      setError(t(language, "plans.openFromTelegram"));
      return;
    }

    try {
      setLoadingCode(plan.code);
      setError("");

      const order = await createOrder({
        telegram_user_id: backendUser.telegram_user_id,
        plan_code: plan.code,
        email: null,
        payment_method: "card",
      });

      const payment = await createPayment({
        order_id: order.id,
        provider: "cards",
        method: "card",
      });

      router.push(
        `/checkout?planName=${encodeURIComponent(plan.name)}&amount=${plan.price}&currency=${plan.currency}&credits=${plan.credits_amount}&orderId=${order.id}&orderNumber=${encodeURIComponent(order.order_number)}&paymentId=${payment.id}`
      );
    } catch {
      setError(t(language, "plans.failedCreate"));
    } finally {
      setLoadingCode("");
    }
  }

  return (
    <main className="page">
      <section className="hero">
        <div className="eyebrow">{t(language, "plans.eyebrow")}</div>
        <h1 className="title">{t(language, "plans.title")}</h1>
        <p className="lead">{t(language, "plans.lead")}</p>
        <div className="hero-meta">
          <span>
            {telegramUser?.id
              ? t(language, "plans.telegramReady")
              : t(language, "plans.browserPreview")}
          </span>
          <Link className="button secondary" href="/wallet">
            {t(language, "common.wallet")}
          </Link>
        </div>
      </section>

      {error ? <div className="notice">{error}</div> : null}

      <section className="pricing-grid">
        {plans.map((plan) => (
          <article
            className={`card plan-card ${plan.code === "pro" ? "featured" : ""}`}
            key={plan.code}
          >
            <div className="badge-row">
              <span className="subtitle">{plan.name}</span>
              <span className={`badge ${plan.code === "pro" ? "hot" : ""}`}>
                {plan.code === "pro"
                  ? t(language, "plans.mostBalanced")
                  : t(language, "plans.days", { days: plan.duration_days ?? 30 })}
              </span>
            </div>
            <div className="price">
              {formatCurrency(plan.price, plan.currency, language)}
            </div>
            <p className="lead">
              {plan.description || t(language, "plans.defaultDescription")}
            </p>
            <div className="stack">
              <div className="detail-row">
                <span className="muted">{t(language, "plans.credits")}</span>
                <strong>{plan.credits_amount}</strong>
              </div>
              <div className="detail-row">
                <span className="muted">{t(language, "plans.billingCycle")}</span>
                <strong>{t(language, "plans.days", { days: plan.duration_days ?? 30 })}</strong>
              </div>
            </div>
            <button
              className="button full"
              onClick={() => handleBuy(plan)}
              disabled={loadingCode === plan.code}
            >
              {loadingCode === plan.code
                ? t(language, "plans.creatingOrder")
                : t(language, "plans.goToCheckout")}
            </button>
          </article>
        ))}
      </section>
    </main>
  );
}

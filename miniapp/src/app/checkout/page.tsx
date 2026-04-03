import CheckoutClient from "./checkout-client";

type CheckoutPageProps = {
  searchParams: Promise<{
    planName?: string;
    amount?: string;
    currency?: string;
    credits?: string;
    orderId?: string;
    orderNumber?: string;
    paymentId?: string;
    cardNumber?: string;
    cardOwner?: string;
    visaCardNumber?: string;
    visaCardOwner?: string;
    alreadyPending?: string;
  }>;
};

export default async function CheckoutPage({ searchParams }: CheckoutPageProps) {
  const params = await searchParams;

  return (
    <CheckoutClient
      planName={params.planName}
      amount={params.amount}
      currency={params.currency}
      credits={params.credits}
      orderId={params.orderId}
      orderNumber={params.orderNumber}
      paymentId={params.paymentId}
      cardNumber={params.cardNumber}
      cardOwner={params.cardOwner}
      visaCardNumber={params.visaCardNumber}
      visaCardOwner={params.visaCardOwner}
      alreadyPending={params.alreadyPending}
    />
  );
}

function getLocale(language?: string) {
  return language === "uz" ? "uz-UZ" : "ru-RU";
}

export function formatCurrency(amount: number, currency: string, language = "ru") {
  return new Intl.NumberFormat(getLocale(language), {
    style: "currency",
    currency,
    maximumFractionDigits: currency === "USD" ? 2 : 0,
  }).format(amount);
}

export function formatDate(value?: string | null, language = "ru") {
  if (!value) {
    return language === "uz" ? "Sanasiz" : "Без даты";
  }

  return new Intl.DateTimeFormat(getLocale(language), {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

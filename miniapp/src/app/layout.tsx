import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "BATIR AI",
  description: "Telegram Mini App for BATIR AI",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}

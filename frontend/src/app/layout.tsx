import type { Metadata } from "next";

import { LocaleProvider } from "@/components/locale-provider";
import { getLocale } from "@/lib/locale";

import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const locale = await getLocale();
  return {
    title:
      locale === "fr" ? "haccpFlow — Gestion HACCP" : "haccpFlow — HACCP management",
    description:
      locale === "fr"
        ? "Suivi des températures et des plans de maîtrise sanitaire."
        : "Temperature monitoring and food safety management plans.",
  };
}

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const locale = await getLocale();
  return (
    <html lang={locale}>
      <body className="min-h-screen antialiased">
        <LocaleProvider initialLocale={locale}>{children}</LocaleProvider>
      </body>
    </html>
  );
}

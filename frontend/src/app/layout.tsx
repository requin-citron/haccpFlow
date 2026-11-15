import type { Metadata, Viewport } from "next";

import { LocaleProvider } from "@/components/locale-provider";
import { PwaRegistration } from "@/components/pwa-registration";
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
    applicationName: "haccpFlow",
    manifest: "/manifest.webmanifest",
    icons: {
      icon: [
        { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
        { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
      ],
      apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180" }],
    },
    appleWebApp: {
      capable: true,
      title: "haccpFlow",
      statusBarStyle: "black-translucent",
    },
  };
}

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#0f172a",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const locale = await getLocale();
  return (
    <html lang={locale}>
      <body className="min-h-screen antialiased">
        <LocaleProvider initialLocale={locale}>
          <PwaRegistration />
          {children}
        </LocaleProvider>
      </body>
    </html>
  );
}

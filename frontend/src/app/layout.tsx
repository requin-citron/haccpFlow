import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "haccpFlow — Gestion HACCP",
  description: "Suivi des températures et des plans de maîtrise sanitaire.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}

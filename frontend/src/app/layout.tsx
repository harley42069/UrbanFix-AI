import type { Metadata } from "next";
import type { ReactNode } from "react";
import Link from "next/link";
import "./globals.css";

import AppProviders from "@/components/AppProviders";
import NavLink from "@/components/NavLink";

export const metadata: Metadata = {
  title: {
    default: "UrbanFix AI",
    template: "%s · UrbanFix AI"
  },
  description: "Plateforme municipale UrbanFix AI pour la gestion des signalements et des scenarii de rehabilitation"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr">
      <body>
        <AppProviders>
          <div className="min-h-screen bg-municipal-shell text-slate-900">
            <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/85 backdrop-blur-xl">
              <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-4 py-4 lg:px-8">
                <Link href="/" className="flex items-center text-lg font-black tracking-tight text-slate-900">
                  <span className="font-bold text-lg">UrbanFix AI</span>
                  <img
                    src="https://flagcdn.com/24x18/tn.png"
                    alt="Tunisie"
                    width="24"
                    height="18"
                    className="inline-block ml-2 rounded-sm"
                  />
                </Link>
              <nav className="flex items-center justify-end gap-3 text-sm font-medium text-slate-700">
                  <NavLink />
                <Link href="/login" className="rounded-full bg-[#1f6fb2] px-4 py-2 text-white hover:bg-[#185b90]">
                  Connexion
                </Link>
              </nav>
              </div>
            </header>

            <main className="mx-auto w-full max-w-7xl px-4 py-8 lg:px-8">{children}</main>

            <footer id="footer" className="border-t border-[#e8d5c0] bg-[#fdf6ec]">
              <div className="mx-auto flex w-full max-w-7xl items-center justify-center px-4 py-3 text-xs text-[#8b6f5e] lg:px-8">
                <p>UrbanFix AI · Gestion intelligente des signalements urbains · Tunisie 🇹🇳</p>
              </div>
            </footer>
          </div>
        </AppProviders>
      </body>
    </html>
  );
}

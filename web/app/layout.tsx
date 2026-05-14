/**
 * Root layout — Next.js App Router entrypoint.
 *
 * Mounts Geist Sans + Geist Mono via next/font/google, forces
 * `data-theme="dark"` on <html> so the design-token block in globals.css
 * always resolves, and wraps the tree in the SWR provider for any client-side
 * refetches that happen below the page-level server fetch.
 */
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { SwrProvider } from "@/lib/swr-provider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Paczkomat Atlas — InPost network analytics",
  description:
    "Locker density per 10k inhabitants across 14 European markets. Polish dominance, network mix, and expansion velocity — live from the InPost public API.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      data-theme="dark"
      className={`${geistSans.variable} ${geistMono.variable}`}
    >
      <body>
        <SwrProvider>{children}</SwrProvider>
      </body>
    </html>
  );
}

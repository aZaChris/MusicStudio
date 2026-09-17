import type { Metadata } from "next";
import { Nunito_Sans, Poppins } from "next/font/google";
import { cookies } from "next/headers";

import { getLocale } from "@/lib/get-locale";
import "./globals.css";

const poppins = Poppins({
  variable: "--font-poppins",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

const nunitoSans = Nunito_Sans({
  variable: "--font-nunito-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "MusicStudio",
  description: "Manage students, lessons, packages, payments, and parent communication.",
};

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const [locale, cookieStore] = await Promise.all([getLocale(), cookies()]);
  const theme = cookieStore.get("musicstudio-theme")?.value === "dark" ? "dark" : "light";

  return (
    <html lang={locale} data-theme={theme} className={`${poppins.variable} ${nunitoSans.variable}`}>
      <body>{children}</body>
    </html>
  );
}

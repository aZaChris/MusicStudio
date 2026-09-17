"use client";

import { useRouter } from "next/navigation";

import type { Locale } from "@/lib/i18n";

export function LanguageToggle({ locale }: { locale: Locale }) {
  const router = useRouter();

  const toggle = () => {
    const next: Locale = locale === "it" ? "en" : "it";
    document.cookie = `musicstudio-locale=${next}; path=/; max-age=31536000`;
    router.refresh();
  };

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={locale === "it" ? "Switch to English" : "Passa all'italiano"}
    >
      {locale === "it" ? "EN" : "IT"}
    </button>
  );
}

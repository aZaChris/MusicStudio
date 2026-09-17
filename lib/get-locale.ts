import "server-only";
import { cookies } from "next/headers";

import type { Locale } from "./i18n";

export async function getLocale(): Promise<Locale> {
  const store = await cookies();
  const cookieLocale = store.get("musicstudio-locale")?.value;
  return cookieLocale === "it" ? "it" : "en";
}

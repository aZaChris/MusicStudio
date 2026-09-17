"use server";

import { AuthError } from "next-auth";

import { signIn, signOut } from "@/lib/auth";

export async function signOutAction() {
  await signOut({ redirectTo: "/login" });
}

export async function signInAction(_prevState: string | null, formData: FormData) {
  try {
    await signIn("credentials", {
      email: formData.get("email"),
      password: formData.get("password"),
      redirectTo: "/",
    });
    return null;
  } catch (err) {
    if (err instanceof AuthError) return "invalid_credentials";
    throw err;
  }
}

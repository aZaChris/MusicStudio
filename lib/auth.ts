import { compare } from "bcryptjs";
import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";

import { getDb } from "./db";
import { users } from "./db/schema";
import { eq } from "drizzle-orm";

export type Role = "teacher" | "studio_owner" | "parent";

export const { handlers, auth, signIn, signOut } = NextAuth({
  session: { strategy: "jwt" },
  pages: { signIn: "/login" },
  providers: [
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      authorize: async (credentials) => {
        const email = credentials?.email as string | undefined;
        const password = credentials?.password as string | undefined;
        if (!email || !password) return null;

        const db = getDb();
        const [user] = await db.select().from(users).where(eq(users.email, email)).limit(1);
        if (!user) return null;

        const valid = await compare(password, user.passwordHash);
        if (!valid) return null;

        return {
          id: String(user.id),
          email: user.email,
          role: user.role,
          preferredLanguage: user.preferredLanguage,
        };
      },
    }),
  ],
  callbacks: {
    jwt: ({ token, user }) => {
      if (user) {
        token.userId = Number(user.id);
        token.role = user.role as Role;
        token.preferredLanguage = user.preferredLanguage as "en" | "it";
      }
      return token;
    },
    session: ({ session, token }) => {
      session.user.id = String(token.userId);
      session.user.role = token.role as Role;
      session.user.preferredLanguage = token.preferredLanguage as "en" | "it";
      return session;
    },
  },
});

import type { Role } from "@/lib/auth";

declare module "@auth/core/types" {
  interface User {
    role: Role;
    preferredLanguage: "en" | "it";
  }

  interface Session {
    user: {
      // kept as `string` (not `number`) so this stays structurally compatible
      // with the base Session/User types — parse with Number(...) at call sites.
      id: string;
      email: string;
      role: Role;
      preferredLanguage: "en" | "it";
    };
  }
}

declare module "@auth/core/jwt" {
  interface JWT {
    userId: number;
    role: Role;
    preferredLanguage: "en" | "it";
  }
}

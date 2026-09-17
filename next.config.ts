import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async headers() {
    return [
      {
        // /api/v1/* is Bearer-token auth (not cookie/CSRF-based), so it's
        // safe to allow cross-origin calls — the React Native app's Expo
        // web preview runs on a different origin during development, and
        // native builds don't send an Origin header at all.
        source: "/api/v1/:path*",
        headers: [
          { key: "Access-Control-Allow-Origin", value: "*" },
          { key: "Access-Control-Allow-Methods", value: "GET, POST, PATCH, DELETE, OPTIONS" },
          { key: "Access-Control-Allow-Headers", value: "Content-Type, Authorization" },
        ],
      },
    ];
  },
};

export default nextConfig;

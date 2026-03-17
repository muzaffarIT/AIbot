import path from "node:path";
import type { NextConfig } from "next";

function normalizeOrigin(value: string | undefined) {
  return value?.trim().replace(/\/$/, "") || undefined;
}

const backendProxyOrigin =
  normalizeOrigin(process.env.BACKEND_INTERNAL_URL) ||
  normalizeOrigin(process.env.NEXT_PUBLIC_BACKEND_URL) ||
  "http://127.0.0.1:8000";

const allowedDevOrigins = [
  process.env.MINIAPP_URL,
  ...(process.env.ALLOWED_DEV_ORIGINS?.split(",") || []),
]
  .map((value) => normalizeOrigin(value))
  .filter((value): value is string => Boolean(value))
  .map((value) => value.replace(/^https?:\/\//, ""));

const nextConfig: NextConfig = {
  allowedDevOrigins,
  outputFileTracingRoot: path.join(__dirname, ".."),
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendProxyOrigin}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;

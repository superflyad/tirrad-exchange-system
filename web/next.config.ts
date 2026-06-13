import path from "node:path";

import type { NextConfig } from "next";

const DEFAULT_API_ORIGIN = "http://127.0.0.1:8000";
const LOCAL_PROXY_BASE = "/api/tes";

function apiRewriteTarget(): string {
  const localApiOrigin = process.env.TES_API_ORIGIN?.trim();
  if (localApiOrigin) {
    return localApiOrigin.endsWith("/") ? localApiOrigin.slice(0, -1) : localApiOrigin;
  }

  const configured = process.env.NEXT_PUBLIC_TES_API_URL?.trim();
  if (!configured || configured === LOCAL_PROXY_BASE) {
    return DEFAULT_API_ORIGIN;
  }
  return configured.endsWith("/") ? configured.slice(0, -1) : configured;
}

const nextConfig: NextConfig = {
  turbopack: {
    root: path.resolve(__dirname),
  },
  async rewrites() {
    return [
      {
        source: `${LOCAL_PROXY_BASE}/:path*`,
        destination: `${apiRewriteTarget()}/:path*`,
      },
    ];
  },
};

export default nextConfig;

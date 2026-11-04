import type { NextConfig } from "next";
const nextConfig: NextConfig = {
  experimental: { proxyTimeout: 240000 },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.API_BASE_URL || "http://127.0.0.1:8000"}/api/:path*`,
      },
    ];
  },
};
export default nextConfig;

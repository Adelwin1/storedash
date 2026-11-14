import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/health",
        destination: "https://storedash-api.onrender.com/health",
      },
      {
        source: "/api/:path*",
        destination: "https://storedash-api.onrender.com/api/:path*",
      },
    ];
  },
};

export default nextConfig;

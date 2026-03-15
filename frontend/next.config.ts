import type { NextConfig } from "next";

const API_PORT = process.env.BORD_API_PORT || "8765";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/python/:path*",
        destination: `http://127.0.0.1:${API_PORT}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;

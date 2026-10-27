import type { NextConfig } from "next";
import { resolve } from "node:path";

const apiOrigin = process.env.ACCOS_API_ORIGIN;

const nextConfig: NextConfig = {
  compress: false,
  output: "standalone",
  outputFileTracingRoot: resolve(process.cwd(), "../.."),
  reactStrictMode: true,
  transpilePackages: ["@accos/api-client", "@accos/ui"],
  rewrites() {
    if (!apiOrigin) return Promise.resolve([]);
    return Promise.resolve([
      {
        source: "/api/v1/:path*",
        destination: `${apiOrigin}/api/v1/:path*`,
      },
    ]);
  },
};

export default nextConfig;

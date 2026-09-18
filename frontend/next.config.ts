import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable React Strict Mode for better development experience
  reactStrictMode: true,

  // Experimental features
  experimental: {
    // LLM report generation can take 1-5 minutes with local models
    proxyTimeout: 600_000, // 10 minutes
  },

  // Image optimization configuration
  images: {
    // 全站沒有任何 next/image 使用；優化器 + `hostname: "**"` 等於提供一個
    // 對任意遠端網址開放的圖片代理（SSRF／雲端 metadata／流量放大）。
    // 需要時再打開，並把 remotePatterns 收斂到實際使用的網域。
    unoptimized: true,
    remotePatterns: [],
    // Image sizes for responsive images
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
    // Output format
    formats: ["image/avif", "image/webp"],
    // Minimum cache TTL for optimized images (in seconds)
    minimumCacheTTL: 60 * 60 * 24 * 30, // 30 days
  },

  // Output configuration for Docker deployment
  output: "standalone",

  // API proxy configuration
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        // 預設埠是 8000（後端實際埠）；8080 是舊的錯誤預設值。
        // 容器部署時由 compose 注入 BACKEND_URL=http://backend:8000。
        destination: `${
          process.env.BACKEND_URL ?? "http://127.0.0.1:8000"
        }/api/:path*`,
      },
    ];
  },

  // Headers for security
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "X-DNS-Prefetch-Control",
            value: "on",
          },
          {
            key: "X-Frame-Options",
            value: "SAMEORIGIN",
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
        ],
      },
      {
        // Static assets caching
        source: "/static/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable",
          },
        ],
      },
      {
        // Image caching
        source: "/_next/image/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=2592000, stale-while-revalidate=86400",
          },
        ],
      },
    ];
  },
};

export default nextConfig;

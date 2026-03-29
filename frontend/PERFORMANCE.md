# Frontend Performance Optimization Guide

This document outlines the performance optimizations applied to the Next.js frontend.

## Table of Contents

1. [Next.js Configuration](#1-nextjs-configuration)
2. [Image Optimization](#2-image-optimization)
3. [Route Prefetching](#3-route-prefetching)
4. [ISR (Incremental Static Regeneration)]#4-isr-incremental-static-regeneration)

---

## 1. Next.js Configuration

### Key Settings in `next.config.ts`

```typescript
// Output standalone for Docker
output: "standalone",

// React Strict Mode
reactStrictMode: true,

// Security Headers
headers: [
  { key: "X-Frame-Options", value: "SAMEORIGIN" },
  { key: "X-Content-Type-Options", value: "nosniff" },
]
```

---

## 2. Image Optimization

### Using `next/image`

Replace all `<img>` tags with Next.js `<Image>` component:

```tsx
import Image from "next/image";

// Before
<img src="/logo.png" alt="Logo" />

// After
<Image
  src="/logo.png"
  alt="Logo"
  width={200}
  height={100}
  priority // For above-fold images
  loading="lazy" // For below-fold images
/>
```

### Best Practices

1. **Always specify width and height** to prevent layout shift
2. **Use `priority` for critical images** (hero, logo)
3. **Use `loading="lazy"` for non-critical images**
4. **Use responsive images**:

```tsx
<Image
  src="/hero.jpg"
  alt="Hero"
  fill
  sizes="(max-width: 768px) 100vw, 50vw"
  className="object-cover"
  priority
/>
```

### Supported Formats

Next.js automatically serves modern formats:
- **AVIF** (best compression)
- **WebP** (wide support)

---

## 3. Route Prefetching

### Automatic Prefetching

Next.js automatically prefetches routes when they appear in the viewport:

```tsx
import Link from "next/link";

// Automatic prefetch when in viewport
<Link href="/agent">Agent Workspace</Link>
```

### Manual Prefetching

For more control, use `useRouter`:

```tsx
"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

export function PrefetchLinks() {
  const router = useRouter();
  
  useEffect(() => {
    // Prefetch likely next pages
    router.prefetch("/agent");
    router.prefetch("/rag");
  }, [router]);
  
  return null;
}
```

### Conditional Prefetching

Disable prefetch for less likely routes:

```tsx
<Link href="/reports" prefetch={false}>
  Reports
</Link>
```

---

## 4. ISR (Incremental Static Regeneration)

### Static Pages with Revalidation

For pages that don't change frequently:

```tsx
// app/landing/page.tsx
export const revalidate = 3600; // Revalidate every hour

export default function LandingPage() {
  return <div>Static content</div>;
}
```

### Dynamic Pages with ISR

```tsx
// app/stats/[id]/page.tsx
export const revalidate = 60; // Revalidate every minute

export async function generateStaticParams() {
  const stats = await fetchStats();
  return stats.map((stat) => ({ id: stat.id }));
}

export default async function StatPage({ params }) {
  const data = await fetchStatData(params.id);
  return <StatView data={data} />;
}
```

### On-Demand Revalidation

Create an API route to trigger revalidation:

```tsx
// app/api/revalidate/route.ts
import { revalidatePath, revalidateTag } from "next/cache";
import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const { path, tag, secret } = await request.json();
  
  if (secret !== process.env.REVALIDATION_SECRET) {
    return NextResponse.json({ error: "Invalid secret" }, { status: 401 });
  }
  
  if (path) {
    revalidatePath(path);
  }
  if (tag) {
    revalidateTag(tag);
  }
  
  return NextResponse.json({ revalidated: true, now: Date.now() });
}
```

---

## 5. Additional Optimizations

### Font Optimization

Use `next/font` for optimized fonts:

```tsx
// app/layout.tsx
import { Inter } from "next/font/google";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export default function RootLayout({ children }) {
  return (
    <html lang="zh-TW" className={inter.variable}>
      <body className={inter.className}>{children}</body>
    </html>
  );
}
```

### Bundle Analysis

Add to `package.json`:

```json
{
  "scripts": {
    "analyze": "ANALYZE=true npm run build"
  }
}
```

### Lazy Loading Components

```tsx
import dynamic from "next/dynamic";

const HeavyComponent = dynamic(
  () => import("@/components/heavy-component"),
  {
    loading: () => <p>Loading...</p>,
    ssr: false, // Disable SSR if not needed
  }
);
```

---

## 6. Performance Checklist

- [x] Enable `output: "standalone"` for Docker
- [x] Configure image optimization
- [x] Add security headers
- [x] Use `next/font` for fonts
- [ ] Replace `<img>` with `<Image>`
- [ ] Add `priority` to above-fold images
- [ ] Implement ISR for static pages
- [ ] Use dynamic imports for heavy components
- [ ] Enable bundle analysis
- [ ] Add loading states for async components

---

## 7. Monitoring

### Web Vitals

Track Core Web Vitals:

```tsx
// app/layout.tsx
export function reportWebVitals(metric) {
  console.log(metric);
  // Send to analytics service
}
```

### Key Metrics to Monitor

- **LCP** (Largest Contentful Paint): < 2.5s
- **FID** (First Input Delay): < 100ms
- **CLS** (Cumulative Layout Shift): < 0.1
- **TTFB** (Time to First Byte): < 600ms

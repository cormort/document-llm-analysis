import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge conditional class names and resolve Tailwind class conflicts.
 *
 * Standard shadcn/ui helper (see `components.json` → `aliases.utils`).
 * This file was missing from the repository because the root `.gitignore`
 * pattern `lib/` (a Python packaging rule) also matched `frontend/src/lib/`.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

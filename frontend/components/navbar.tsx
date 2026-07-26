"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/lib/auth-context";

export function NavBar() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const [loggingOut, setLoggingOut] = useState(false);

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await logout();
      router.push("/courses");
    } catch {
      // Session may already be gone; the /me refresh on next load settles it.
    } finally {
      setLoggingOut(false);
    }
  }

  return (
    <header className="border-b border-black/10 dark:border-white/15">
      <nav className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3">
        <Link href="/courses" className="font-semibold tracking-tight">
          SkillForge
        </Link>
        <div className="flex items-center gap-4 text-sm">
          {loading ? null : user ? (
            <>
              <span className="text-black/60 dark:text-white/60">
                {user.full_name || user.email}
              </span>
              <button
                onClick={handleLogout}
                disabled={loggingOut}
                className="rounded border border-black/15 px-3 py-1 hover:bg-black/5 disabled:opacity-50 dark:border-white/20 dark:hover:bg-white/10"
              >
                {loggingOut ? "Logging out…" : "Log out"}
              </button>
            </>
          ) : (
            <Link
              href="/login"
              className="rounded border border-black/15 px-3 py-1 hover:bg-black/5 dark:border-white/20 dark:hover:bg-white/10"
            >
              Log in
            </Link>
          )}
        </div>
      </nav>
    </header>
  );
}

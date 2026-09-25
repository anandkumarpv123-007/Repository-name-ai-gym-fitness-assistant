"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function FloatingGymBuddy() {
  const router = useRouter();
  const pathname = usePathname();
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("access_token") || localStorage.getItem("token");
    setIsAuthenticated(!!token);
  }, [pathname]);

  // Don't render on auth pages or when already on gym buddy page
  if (pathname === "/login" || pathname === "/register" || pathname === "/buddy") {
    return null;
  }

  return (
    <button
      type="button"
      onClick={() => router.push(isAuthenticated ? "/buddy" : "/login?redirect=/buddy")}
      className="fixed bottom-6 right-6 z-50 flex items-center gap-2.5 rounded-full border border-teal-500/50 bg-slate-900/90 px-4 py-3 shadow-2xl backdrop-blur-md transition-all hover:scale-105 hover:bg-slate-800 hover:border-teal-400 group"
      title="Ask Virtual Gym Buddy"
      aria-label="Ask Virtual Gym Buddy"
    >
      <div className="relative flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-tr from-teal-500 to-blue-500 text-lg shadow-md">
        🤖
        <span className="absolute -top-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-emerald-400 border-2 border-slate-900 animate-pulse" />
      </div>
      <span className="text-xs font-semibold text-slate-100 hidden sm:inline group-hover:text-teal-300">
        Gym Buddy
      </span>
    </button>
  );
}

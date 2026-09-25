"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { API_BASE_URL } from "@/api/config";

interface WorkoutHistoryItem {
  id?: number;
  session_id?: number;
  started_at: string;
  ended_at?: string | null;
  performance_score: number | null;
  calories: number | null;
  notes?: string | null;
  exercise_name?: string;
  sets?: number;
  reps?: number;
  exercises?: {
    name: string;
    category: string;
    sets: number;
    reps: number;
  }[];
}

interface PerformanceSummary {
  total_workouts?: number;
  total_sessions?: number;
  total_reps?: number;
  average_performance_score?: number | null;
  average_score?: number | null;
  trend?: string;
  score_trend?: string;
  score_delta?: number | null;
  top_focus_areas?: string[];
  next_week_focus?: string;
  recurring_issue?: string;
  recent_sessions?: {
    session_id: number;
    date: string;
    exercise: string;
    score: number | null;
    reps: number;
  }[];
}

export default function HistoryPage() {
  const router = useRouter();
  const [history, setHistory] = useState<WorkoutHistoryItem[]>([]);
  const [summary, setSummary] = useState<PerformanceSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
      return;
    }

    async function loadData() {
      try {
        setLoading(true);
        const headers = { Authorization: `Bearer ${token}` };

        const [historyRes, summaryRes] = await Promise.all([
          fetch(`${API_BASE_URL}/workouts/history`, { headers }),
          fetch(`${API_BASE_URL}/performance/summary`, { headers }),
        ]);

        if (historyRes.status === 401 || summaryRes.status === 401) {
          localStorage.removeItem("access_token");
          router.push("/login");
          return;
        }

        if (!historyRes.ok || !summaryRes.ok) {
          throw new Error("Failed to load workout performance data");
        }

        const historyData = await historyRes.json();
        const summaryData = await summaryRes.json();

        setHistory(historyData);
        setSummary(summaryData);
      } catch (err: unknown) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Error fetching workout history");
        }
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [router]);

  const getScoreBadge = (score: number | null) => {
    if (score === null) return <span className="text-slate-500">Unscored</span>;
    if (score >= 85) {
      return (
        <span className="rounded-full bg-emerald-950 border border-emerald-700 px-2.5 py-1 text-xs font-bold text-emerald-300">
          {score} • Excellent
        </span>
      );
    }
    if (score >= 70) {
      return (
        <span className="rounded-full bg-blue-950 border border-blue-700 px-2.5 py-1 text-xs font-bold text-blue-300">
          {score} • Good
        </span>
      );
    }
    return (
      <span className="rounded-full bg-amber-950 border border-amber-700 px-2.5 py-1 text-xs font-bold text-amber-300">
        {score} • Needs Work
      </span>
    );
  };

  const getTrendBadge = (trend: string, delta: number | null) => {
    if (trend === "IMPROVING") {
      return (
        <span className="rounded-md bg-emerald-900/60 border border-emerald-600 px-2 py-0.5 text-xs font-semibold text-emerald-300">
          ▲ Improving {delta ? `(+${delta})` : ""}
        </span>
      );
    }
    if (trend === "DECLINING") {
      return (
        <span className="rounded-md bg-rose-900/60 border border-rose-600 px-2 py-0.5 text-xs font-semibold text-rose-300">
          ▼ Declining {delta ? `(${delta})` : ""}
        </span>
      );
    }
    return (
      <span className="rounded-md bg-slate-800 border border-slate-700 px-2 py-0.5 text-xs font-semibold text-slate-300">
        ● Stable
      </span>
    );
  };

  return (
    <main className="min-h-screen bg-slate-950 p-4 md:p-8 text-white">
      {/* Header */}
      <header className="mx-auto flex max-w-6xl items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold bg-gradient-to-r from-blue-400 to-teal-400 bg-clip-text text-transparent">
            Workout History & Analytics
          </h1>
          <p className="text-xs md:text-sm text-slate-400 mt-1">
            Historical Session Performance & Longitudinal Biomechanics
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/reports"
            className="rounded-lg border border-teal-600/50 bg-teal-950/40 px-3.5 py-2 text-xs md:text-sm font-medium text-teal-300 hover:bg-teal-900/60 transition"
          >
            Weekly Intelligence
          </Link>
          <Link
            href="/nutrition"
            className="rounded-lg border border-emerald-600/50 bg-emerald-950/40 px-3.5 py-2 text-xs md:text-sm font-medium text-emerald-300 hover:bg-emerald-900/60 transition"
          >
            Nutrition
          </Link>
          <Link
            href="/workout"
            className="rounded-lg bg-blue-600 px-4 py-2 text-xs md:text-sm font-medium text-white hover:bg-blue-500 transition"
          >
            + Start Workout
          </Link>
          <Link
            href="/dashboard"
            className="rounded-lg border border-slate-700 px-4 py-2 text-xs md:text-sm font-medium hover:bg-slate-800 transition"
          >
            Dashboard
          </Link>
        </div>
      </header>

      {error && (
        <div className="mx-auto mt-4 max-w-6xl rounded-lg border border-red-800 bg-red-950/40 p-4 text-sm text-red-300">
          ⚠️ {error}
        </div>
      )}

      {loading ? (
        <div className="mx-auto mt-16 max-w-6xl text-center text-slate-400">
          <p>Loading your workout analytics...</p>
        </div>
      ) : (
        <div className="mx-auto mt-8 max-w-6xl space-y-8">
          {/* Summary Overview Cards */}
          {summary && (
            <section className="grid gap-4 md:grid-cols-4">
              <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                <span className="text-xs text-slate-400 uppercase tracking-wider">Avg Score</span>
                <p className="mt-2 text-3xl font-bold text-teal-400">
                  {summary.average_performance_score ?? summary.average_score ?? "—"}
                  <span className="text-sm font-normal text-slate-500"> / 100</span>
                </p>
                <div className="mt-2 flex items-center gap-2">
                  {getTrendBadge(summary.trend ?? summary.score_trend ?? "STABLE", summary.score_delta ?? null)}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                <span className="text-xs text-slate-400 uppercase tracking-wider">Workouts Logged</span>
                <p className="mt-2 text-3xl font-bold text-white">{summary.total_workouts ?? summary.total_sessions ?? 0}</p>
                <p className="text-xs text-slate-500 mt-1">Completed sessions</p>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                <span className="text-xs text-slate-400 uppercase tracking-wider">Total Repetitions</span>
                <p className="mt-2 text-3xl font-bold text-white">{summary.total_reps ?? 0}</p>
                <p className="text-xs text-slate-500 mt-1">Vision verified reps</p>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                <span className="text-xs text-slate-400 uppercase tracking-wider">Top Coaching Focus</span>
                <p className="mt-2 text-sm font-medium text-slate-200">
                  {summary.top_focus_areas && summary.top_focus_areas.length > 0
                    ? summary.top_focus_areas[0]
                    : summary.next_week_focus || summary.recurring_issue || "Maintain consistent form"}
                </p>
                <p className="text-xs text-slate-500 mt-1">Biomechanical priority</p>
              </div>
            </section>
          )}

          {/* Detailed Workout History Table */}
          <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Completed Sessions</h2>

            {history.length === 0 ? (
              <div className="py-12 text-center text-slate-400 space-y-4">
                <p>No workout sessions logged yet.</p>
                <Link
                  href="/workout"
                  className="inline-block rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-500 transition"
                >
                  Start Your First AI Gym Workout
                </Link>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-300">
                  <thead className="border-b border-slate-800 text-xs uppercase text-slate-400">
                    <tr>
                      <th className="py-3 px-4">Session Date</th>
                      <th className="py-3 px-4">Exercise</th>
                      <th className="py-3 px-4">Sets / Reps</th>
                      <th className="py-3 px-4">Performance Score</th>
                      <th className="py-3 px-4">Calories</th>
                      <th className="py-3 px-4">Notes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {history.map((item, idx) => {
                      const idKey = item.id || item.session_id || idx;
                      const exName = item.exercise_name || (item.exercises && item.exercises[0]?.name) || "Squat";
                      const exCategory = (item.exercises && item.exercises[0]?.category) || "Compound";
                      const sets = item.sets ?? (item.exercises && item.exercises[0]?.sets) ?? 1;
                      const reps = item.reps ?? (item.exercises && item.exercises[0]?.reps) ?? 0;

                      return (
                        <tr key={idKey} className="hover:bg-slate-800/40 transition">
                          <td className="py-3 px-4 font-mono text-xs text-slate-400">
                            {item.started_at ? new Date(item.started_at).toLocaleString() : "Recent"}
                          </td>
                          <td className="py-3 px-4 font-semibold text-white">
                            {exName}
                            <span className="ml-1.5 text-xs text-slate-500 font-normal">
                              ({exCategory})
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            {sets} set{sets > 1 ? "s" : ""} × {reps} reps
                          </td>
                          <td className="py-3 px-4">{getScoreBadge(item.performance_score)}</td>
                          <td className="py-3 px-4 font-mono text-xs text-emerald-400">
                            {item.calories ? `${item.calories} kcal` : "—"}
                          </td>
                          <td className="py-3 px-4 text-xs text-slate-400 max-w-xs truncate">
                            {item.notes || "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}
    </main>
  );
}

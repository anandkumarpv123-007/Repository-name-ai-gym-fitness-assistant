"use client";

import { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { API_BASE_URL } from "@/api/config";

interface ReportingPeriod {
  start_date: string;
  end_date: string;
  days: number;
}

interface ExerciseStatItem {
  name: string;
  category: string;
  total_sessions: number;
  total_reps: number;
  avg_score: number | null;
}

interface FormWarningItem {
  violation_code: string;
  name: string;
  count: number;
  percentage: number;
  severity: string;
}

interface SessionTrendPoint {
  session_id: number;
  date: string;
  score: number | null;
  reps: number;
  exercise: string;
}

interface WeeklyPerformanceResponse {
  reporting_period: ReportingPeriod;
  total_sessions: number;
  total_reps: number;
  average_score: number | null;
  trend: "improving" | "declining" | "stable" | "insufficient_history";
  score_delta: number | null;
  strongest_improvement: string;
  recurring_form_issue: string;
  next_week_focus: string;
  exercise_stats: ExerciseStatItem[];
  form_warnings: FormWarningItem[];
  session_history: SessionTrendPoint[];
}

export default function ReportsPage() {
  const router = useRouter();
  const [data, setData] = useState<WeeklyPerformanceResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");
  const [days, setDays] = useState<number>(7);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
      return;
    }

    async function fetchWeeklyReport() {
      try {
        setLoading(true);
        setError("");
        const res = await fetch(`${API_BASE_URL}/performance/weekly?days=${days}`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (res.status === 401) {
          localStorage.removeItem("access_token");
          router.push("/login");
          return;
        }

        if (!res.ok) {
          const errBody = await res.json().catch(() => ({}));
          throw new Error(errBody.detail || "Failed to load weekly progress report");
        }

        const reportData: WeeklyPerformanceResponse = await res.json();
        setData(reportData);
      } catch (err: unknown) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Error fetching performance report");
        }
      } finally {
        setLoading(false);
      }
    }

    fetchWeeklyReport();
  }, [days, router]);

  // SVG Trend Chart computations
  const chartPoints = useMemo(() => {
    if (!data?.session_history || data.session_history.length === 0) return [];
    return data.session_history.filter((s) => s.score !== null);
  }, [data?.session_history]);

  const svgDimensions = { width: 640, height: 180, padX: 45, padY: 25 };
  const chartPath = useMemo(() => {
    if (chartPoints.length < 2) return "";
    const { width, height, padX, padY } = svgDimensions;
    const chartW = width - 2 * padX;
    const chartH = height - 2 * padY;

    // Y scale: min 40, max 100
    const minY = 40;
    const maxY = 100;
    const rangeY = maxY - minY;

    return chartPoints
      .map((p, idx) => {
        const x = padX + (idx / (chartPoints.length - 1)) * chartW;
        const score = Math.max(minY, Math.min(maxY, p.score ?? 50));
        const y = height - padY - ((score - minY) / rangeY) * chartH;
        return `${idx === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
      })
      .join(" ");
  }, [chartPoints]);

  const getTrendBadge = (trend?: string, delta?: number | null) => {
    if (!trend || trend === "insufficient_history") {
      return (
        <span className="rounded-full bg-slate-800 border border-slate-700 px-3 py-1 text-xs font-semibold text-slate-300">
          ○ Baseline Phase
        </span>
      );
    }
    if (trend === "improving") {
      return (
        <span className="rounded-full bg-emerald-950/80 border border-emerald-600 px-3 py-1 text-xs font-bold text-emerald-300 flex items-center gap-1.5 shadow-sm shadow-emerald-900/30">
          <span className="text-emerald-400">▲</span> Improving {delta !== null && delta !== undefined ? `(+${delta} pts)` : ""}
        </span>
      );
    }
    if (trend === "declining") {
      return (
        <span className="rounded-full bg-rose-950/80 border border-rose-600 px-3 py-1 text-xs font-bold text-rose-300 flex items-center gap-1.5 shadow-sm shadow-rose-900/30">
          <span className="text-rose-400">▼</span> Declining {delta !== null && delta !== undefined ? `(${delta} pts)` : ""}
        </span>
      );
    }
    return (
      <span className="rounded-full bg-amber-950/80 border border-amber-600 px-3 py-1 text-xs font-bold text-amber-300 flex items-center gap-1.5">
        <span className="text-amber-400">●</span> Stable Movement Quality
      </span>
    );
  };

  return (
    <main className="min-h-screen bg-slate-950 p-4 md:p-8 text-white font-sans">
      {/* Navigation Header */}
      <header className="mx-auto flex max-w-6xl flex-col md:flex-row md:items-center justify-between border-b border-slate-800 pb-5 gap-4">
        <div>
          <div className="flex items-center gap-3">
            <span className="rounded-md bg-blue-950 border border-blue-700 px-2.5 py-0.5 text-xs font-bold tracking-wide text-blue-300 uppercase">
              Phase 3 Intelligence
            </span>
            <span className="text-xs text-slate-500">Pose-to-Performance Analyzer</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold bg-gradient-to-r from-blue-400 via-teal-300 to-emerald-400 bg-clip-text text-transparent mt-1.5">
            Weekly Progress Intelligence
          </h1>
          <p className="text-xs md:text-sm text-slate-400 mt-1">
            Biomechanical trend analysis, recurrence detection, and deterministic coaching focus
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Time Window Selector */}
          <div className="flex rounded-lg border border-slate-800 bg-slate-900/80 p-1 text-xs">
            <button
              onClick={() => setDays(7)}
              className={`rounded-md px-3 py-1.5 font-medium transition ${
                days === 7 ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              7 Days
            </button>
            <button
              onClick={() => setDays(14)}
              className={`rounded-md px-3 py-1.5 font-medium transition ${
                days === 14 ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              14 Days
            </button>
            <button
              onClick={() => setDays(30)}
              className={`rounded-md px-3 py-1.5 font-medium transition ${
                days === 30 ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              30 Days
            </button>
          </div>

          <Link
            href="/nutrition"
            className="rounded-lg border border-emerald-600/50 bg-emerald-950/40 px-3.5 py-1.5 text-xs md:text-sm font-medium text-emerald-300 hover:bg-emerald-900/60 transition"
          >
            Nutrition
          </Link>
          <Link
            href="/history"
            className="rounded-lg border border-slate-800 bg-slate-900 px-3.5 py-1.5 text-xs md:text-sm font-medium hover:bg-slate-800 transition"
          >
            History
          </Link>
          <Link
            href="/dashboard"
            className="rounded-lg border border-slate-800 bg-slate-900 px-3.5 py-1.5 text-xs md:text-sm font-medium hover:bg-slate-800 transition"
          >
            Dashboard
          </Link>
          <Link
            href="/workout"
            className="rounded-lg bg-blue-600 px-4 py-1.5 text-xs md:text-sm font-semibold text-white hover:bg-blue-500 shadow-md shadow-blue-600/30 transition"
          >
            + Start Workout
          </Link>
        </div>
      </header>

      {/* Error notification */}
      {error && (
        <div className="mx-auto mt-6 max-w-6xl rounded-xl border border-rose-900/80 bg-rose-950/40 p-4 text-sm text-rose-300 flex items-center justify-between">
          <span>⚠️ {error}</span>
          <button
            onClick={() => setDays(days)}
            className="rounded bg-rose-900/60 px-3 py-1 text-xs font-semibold hover:bg-rose-800"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && !data && (
        <section className="mx-auto mt-8 max-w-6xl space-y-6">
          <div className="grid gap-4 md:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-28 rounded-xl bg-slate-900/60 animate-pulse border border-slate-800/60" />
            ))}
          </div>
          <div className="h-64 rounded-xl bg-slate-900/60 animate-pulse border border-slate-800/60" />
        </section>
      )}

      {/* Main Content */}
      {!loading && data && (
        <>
          {/* Period Subhead */}
          <div className="mx-auto mt-6 max-w-6xl flex items-center justify-between text-xs text-slate-400">
            <div>
              Window: <span className="font-semibold text-slate-200">{data.reporting_period.start_date}</span> to{" "}
              <span className="font-semibold text-slate-200">{data.reporting_period.end_date}</span> ({data.reporting_period.days} days)
            </div>
            <div>{getTrendBadge(data.trend, data.score_delta)}</div>
          </div>

          {/* KPI Summary Cards */}
          <section className="mx-auto mt-4 grid max-w-6xl gap-4 md:grid-cols-4">
            {/* Average Performance Score */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 backdrop-blur shadow-sm">
              <span className="text-xs uppercase tracking-wider text-slate-400">Average Performance</span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-extrabold text-white">
                  {data.average_score !== null ? data.average_score : "—"}
                </span>
                <span className="text-xs text-slate-400">/ 100</span>
              </div>
              <p className="mt-1 text-xs text-slate-400">
                {data.average_score && data.average_score >= 85
                  ? "High biomechanical execution"
                  : data.average_score && data.average_score >= 70
                  ? "Moderate execution quality"
                  : data.average_score
                  ? "Needs technical focus"
                  : "No scored sessions"}
              </p>
            </div>

            {/* Total Workouts */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 backdrop-blur shadow-sm">
              <span className="text-xs uppercase tracking-wider text-slate-400">Total Workouts</span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-extrabold text-white">{data.total_sessions}</span>
                <span className="text-xs text-slate-400">sessions</span>
              </div>
              <p className="mt-1 text-xs text-slate-400">Across current time window</p>
            </div>

            {/* Total Repetitions */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 backdrop-blur shadow-sm">
              <span className="text-xs uppercase tracking-wider text-slate-400">Total Volume</span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-extrabold text-white">{data.total_reps}</span>
                <span className="text-xs text-slate-400">tracked reps</span>
              </div>
              <p className="mt-1 text-xs text-slate-400">Validated by pose state machine</p>
            </div>

            {/* Trajectory */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 backdrop-blur shadow-sm">
              <span className="text-xs uppercase tracking-wider text-slate-400">Movement Trajectory</span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-2xl font-bold capitalize text-slate-100">
                  {data.trend === "insufficient_history" ? "Baseline" : data.trend}
                </span>
              </div>
              <p className="mt-1 text-xs text-slate-400">
                {data.score_delta !== null
                  ? `Half-over-half delta: ${data.score_delta > 0 ? "+" : ""}${data.score_delta} pts`
                  : "Need ≥ 2 sessions for trend"}
              </p>
            </div>
          </section>

          {/* Actionable Next-Week Coaching Focus Banner */}
          <section className="mx-auto mt-6 max-w-6xl rounded-2xl border border-blue-800/40 bg-gradient-to-r from-blue-950/60 via-slate-900 to-indigo-950/40 p-6 shadow-md">
            <div className="flex items-start gap-4">
              <div className="rounded-xl bg-blue-600/20 border border-blue-500/40 p-3 text-2xl text-blue-400 flex-shrink-0">
                🎯
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-blue-400">
                    Next-Week Actionable Coaching Focus
                  </span>
                  <span className="rounded-full bg-blue-900/80 px-2 py-0.5 text-[10px] font-semibold text-blue-300">
                    Rule-Based Intelligence
                  </span>
                </div>
                <h3 className="text-base md:text-lg font-bold text-slate-100">
                  {data.next_week_focus}
                </h3>
                <p className="text-xs md:text-sm text-slate-300">
                  Targeted directly at eliminating your recurring form errors and maximizing repetition quality.
                </p>
              </div>
            </div>
          </section>

          {/* 2-Column Progress Diagnostic Intelligence */}
          <section className="mx-auto mt-6 grid max-w-6xl gap-6 md:grid-cols-2">
            {/* Strongest Improvement Area */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-6 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs uppercase tracking-wider text-emerald-400 font-semibold flex items-center gap-1.5">
                    <span>✨</span> Strongest Measurable Improvement
                  </span>
                  <span className="rounded-full bg-emerald-950/60 border border-emerald-800 px-2 py-0.5 text-[11px] font-bold text-emerald-300">
                    Validated Component
                  </span>
                </div>
                <h4 className="mt-3 text-lg font-bold text-white">
                  {data.strongest_improvement}
                </h4>
                <p className="mt-2 text-xs md:text-sm text-slate-300">
                  Calculated by comparing multi-component performance metrics (ROM, Posture, Stability, Smoothness, Tempo) between your prior and recent workout halves.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-800/80 text-xs text-slate-400 flex items-center gap-2">
                <span className="text-emerald-400">✔</span> Deterministic tie-breaking prioritizing ROM &gt; Posture &gt; Stability
              </div>
            </div>

            {/* Recurring Form Weakness */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-6 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs uppercase tracking-wider text-amber-400 font-semibold flex items-center gap-1.5">
                    <span>⚠️</span> Recurring Form Weakness
                  </span>
                  <span className="rounded-full bg-amber-950/60 border border-amber-800 px-2 py-0.5 text-[11px] font-bold text-amber-300">
                    Highest Severity
                  </span>
                </div>
                <h4 className="mt-3 text-lg font-bold text-white">
                  {data.recurring_form_issue}
                </h4>
                <p className="mt-2 text-xs md:text-sm text-slate-300">
                  Aggregated from pose detection violation logs across all completed repetitions in the selected reporting window.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-800/80 text-xs text-slate-400 flex items-center gap-2">
                <span className="text-amber-400">!</span> Prioritizes Depth &gt; Torso Lean &gt; Knee Alignment
              </div>
            </div>
          </section>

          {/* Section 3.8 Visualizations */}
          <section className="mx-auto mt-6 grid max-w-6xl gap-6 md:grid-cols-3">
            {/* Chart: Session Performance Score Trajectory (2 columns wide) */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-6 md:col-span-2">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div>
                  <h3 className="text-base font-bold text-white">Session Performance Trajectory</h3>
                  <p className="text-xs text-slate-400">Score per session over selected period</p>
                </div>
                <span className="text-xs text-slate-400">{chartPoints.length} scored data points</span>
              </div>

              {chartPoints.length < 2 ? (
                <div className="flex h-48 items-center justify-center text-xs text-slate-500">
                  At least 2 scored sessions are required to plot trend line.
                </div>
              ) : (
                <div className="mt-4 relative">
                  <svg
                    viewBox={`0 0 ${svgDimensions.width} ${svgDimensions.height}`}
                    className="w-full h-48 overflow-visible"
                  >
                    {/* Grid lines */}
                    {[50, 70, 90].map((gridScore) => {
                      const y =
                        svgDimensions.height -
                        svgDimensions.padY -
                        ((gridScore - 40) / 60) * (svgDimensions.height - 2 * svgDimensions.padY);
                      return (
                        <g key={gridScore}>
                          <line
                            x1={svgDimensions.padX}
                            y1={y}
                            x2={svgDimensions.width - svgDimensions.padX}
                            y2={y}
                            stroke="#334155"
                            strokeDasharray="4 4"
                            strokeWidth="1"
                          />
                          <text
                            x={svgDimensions.padX - 8}
                            y={y + 4}
                            textAnchor="end"
                            fontSize="10"
                            fill="#64748b"
                          >
                            {gridScore}
                          </text>
                        </g>
                      );
                    })}

                    {/* Gradient Area under line */}
                    <defs>
                      <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.35" />
                        <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.0" />
                      </linearGradient>
                    </defs>

                    {/* Polyline Path */}
                    <path
                      d={chartPath}
                      fill="none"
                      stroke="#38bdf8"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />

                    {/* Data Points */}
                    {chartPoints.map((p, idx) => {
                      const chartW = svgDimensions.width - 2 * svgDimensions.padX;
                      const chartH = svgDimensions.height - 2 * svgDimensions.padY;
                      const x = svgDimensions.padX + (idx / (chartPoints.length - 1)) * chartW;
                      const score = Math.max(40, Math.min(100, p.score ?? 50));
                      const y = svgDimensions.height - svgDimensions.padY - ((score - 40) / 60) * chartH;
                      return (
                        <g key={p.session_id} className="group">
                          <circle
                            cx={x}
                            cy={y}
                            r="4.5"
                            fill="#0284c7"
                            stroke="#ffffff"
                            strokeWidth="2"
                            className="cursor-pointer transition-transform hover:scale-125"
                          />
                          <text
                            x={x}
                            y={y - 8}
                            textAnchor="middle"
                            fontSize="10"
                            fontWeight="bold"
                            fill="#e2e8f0"
                          >
                            {p.score}
                          </text>
                          <text
                            x={x}
                            y={svgDimensions.height - 5}
                            textAnchor="middle"
                            fontSize="9"
                            fill="#64748b"
                          >
                            {p.date.slice(5)}
                          </text>
                        </g>
                      );
                    })}
                  </svg>
                </div>
              )}
            </div>

            {/* Form Warnings Breakdown */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-6 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div>
                    <h3 className="text-base font-bold text-white">Form Violation Frequency</h3>
                    <p className="text-xs text-slate-400">Observed technical errors</p>
                  </div>
                </div>

                {data.form_warnings.length === 0 ? (
                  <div className="flex h-40 flex-col items-center justify-center text-center text-xs text-emerald-400">
                    <span className="text-2xl mb-1">🎉</span>
                    Clean movement form! No technical violations detected in this window.
                  </div>
                ) : (
                  <div className="mt-4 space-y-4">
                    {data.form_warnings.map((w) => {
                      const barColor =
                        w.severity === "high"
                          ? "bg-rose-500"
                          : w.severity === "moderate"
                          ? "bg-amber-500"
                          : "bg-blue-500";

                      return (
                        <div key={w.violation_code} className="space-y-1">
                          <div className="flex justify-between text-xs">
                            <span className="font-medium text-slate-200">{w.name}</span>
                            <span className="text-slate-400 font-semibold">
                              {w.count}x ({w.percentage}%)
                            </span>
                          </div>
                          <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
                            <div
                              className={`h-full ${barColor} rounded-full transition-all duration-500`}
                              style={{ width: `${Math.min(100, Math.max(8, w.percentage))}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              <p className="mt-4 text-[11px] text-slate-400">
                Fixing high-severity violations unlocks higher Performance Scores in Phase 2.5 engine.
              </p>
            </div>
          </section>

          {/* Exercise Breakdown Table */}
          <section className="mx-auto mt-6 max-w-6xl rounded-xl border border-slate-800 bg-slate-900/80 p-6">
            <h3 className="text-base font-bold text-white">Exercise Breakdown</h3>
            <p className="text-xs text-slate-400 mt-0.5">Aggregated performance per movement pattern</p>

            {data.exercise_stats.length === 0 ? (
              <p className="mt-4 text-xs text-slate-500">No exercise statistics available.</p>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-left text-xs md:text-sm">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400">
                      <th className="py-2.5 font-medium">Exercise</th>
                      <th className="py-2.5 font-medium">Category</th>
                      <th className="py-2.5 font-medium text-right">Sessions</th>
                      <th className="py-2.5 font-medium text-right">Total Reps</th>
                      <th className="py-2.5 font-medium text-right">Avg Score</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {data.exercise_stats.map((ex) => (
                      <tr key={ex.name} className="hover:bg-slate-800/30 transition">
                        <td className="py-3 font-semibold text-slate-100">{ex.name}</td>
                        <td className="py-3 text-slate-400 capitalize">{ex.category}</td>
                        <td className="py-3 text-right text-slate-300">{ex.total_sessions}</td>
                        <td className="py-3 text-right text-slate-300 font-bold">{ex.total_reps}</td>
                        <td className="py-3 text-right font-bold text-blue-400">
                          {ex.avg_score !== null ? ex.avg_score : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* Empty State Banner (if 0 sessions) */}
          {data.total_sessions === 0 && (
            <section className="mx-auto mt-8 max-w-2xl rounded-2xl border border-slate-800 bg-slate-900/90 p-8 text-center">
              <div className="text-4xl mb-3">🏋️‍♂️</div>
              <h3 className="text-lg font-bold text-white">No Workouts Recorded in This Period</h3>
              <p className="mt-2 text-xs md:text-sm text-slate-400 max-w-md mx-auto">
                Complete your first guided workout session with the AI vision trainer to establish your baseline and generate weekly progress analytics.
              </p>
              <Link
                href="/workout"
                className="mt-5 inline-block rounded-xl bg-blue-600 px-6 py-2.5 text-xs md:text-sm font-semibold text-white hover:bg-blue-500 shadow-md shadow-blue-600/30 transition"
              >
                Launch AI Trainer
              </Link>
            </section>
          )}
        </>
      )}
    </main>
  );
}

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE_URL } from "@/api/config";

interface BehavioralFeatureSummary {
  days_since_last_workout: number;
  workout_frequency_7d: number;
  workout_frequency_30d: number;
  avg_weekly_workouts: number;
  consistency_score: number;
  preferred_weekday_ratio: number;
  max_gap_days_30d: number;
  form_score_trend_delta: number;
}

interface BehavioralFactorItem {
  feature_name: string;
  description: string;
  impact_level: string;
  signal_direction: string;
}

interface HabitStatusResponse {
  user_id: number;
  status: string;
  total_sessions_logged: number;
  skip_probability: number | null;
  risk_level: string;
  risk_explanation: string;
  features: BehavioralFeatureSummary;
  behavioral_factors: BehavioralFactorItem[];
  adaptive_nudge: string;
  recommended_schedule: string;
  model_info: Record<string, any>;
  timestamp: string;
}

interface HabitPredictionItem {
  id: number;
  user_id: number;
  prediction_date: string;
  skip_probability: number | null;
  risk_level: string;
  primary_factor: string | null;
  nudge_text: string | null;
  recommended_schedule: string | null;
  created_at: string;
}

export default function HabitTrackerPage() {
  const router = useRouter();
  const [habitStatus, setHabitStatus] = useState<HabitStatusResponse | null>(null);
  const [history, setHistory] = useState<HabitPredictionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      const token = localStorage.getItem("access_token");
      if (!token) {
        router.push("/login");
        return;
      }

      try {
        const [statusRes, historyRes] = await Promise.all([
          fetch(`${API_BASE_URL}/habit/status`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch(`${API_BASE_URL}/habit/history?limit=10`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
        ]);

        if (statusRes.status === 401 || historyRes.status === 401) {
          localStorage.removeItem("access_token");
          router.push("/login");
          return;
        }

        if (!statusRes.ok) {
          const errData = await statusRes.json();
          throw new Error(errData.detail || "Failed to load habit intelligence");
        }

        const statusData: HabitStatusResponse = await statusRes.json();
        setHabitStatus(statusData);

        if (historyRes.ok) {
          const historyData = await historyRes.json();
          setHistory(historyData.predictions || []);
        }
      } catch (err) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Failed to communicate with habit tracking server.");
        }
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [router]);

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-white">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
          <p className="text-slate-400 text-sm">Analyzing behavioral habit telemetry...</p>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-white p-6">
        <div className="max-w-md rounded-2xl border border-red-900 bg-slate-900 p-8 text-center shadow-xl">
          <h1 className="text-2xl font-bold text-red-400">Habit Service Error</h1>
          <p className="mt-3 text-slate-300 text-sm">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-6 rounded-lg bg-red-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-red-500 transition"
          >
            Retry Analysis
          </button>
        </div>
      </main>
    );
  }

  const isColdStart = habitStatus?.status === "insufficient_data" || (habitStatus?.total_sessions_logged ?? 0) < 3;
  const skipProbPercent = habitStatus?.skip_probability !== null && habitStatus?.skip_probability !== undefined
    ? Math.round(habitStatus.skip_probability * 100)
    : null;

  const getRiskBadgeColor = (risk: string) => {
    switch (risk.toLowerCase()) {
      case "low":
        return "border-emerald-500 bg-emerald-950/80 text-emerald-300";
      case "moderate":
        return "border-amber-500 bg-amber-950/80 text-amber-300";
      case "high":
        return "border-rose-500 bg-rose-950/80 text-rose-300";
      default:
        return "border-indigo-500 bg-indigo-950/80 text-indigo-300";
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 text-white p-6 md:p-10">
      <div className="mx-auto max-w-6xl space-y-8">
        
        {/* Header Bar */}
        <header className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-indigo-900/60 border border-indigo-500 px-3 py-0.5 text-xs font-semibold text-indigo-300">
                Behavioral Consistency Engine
              </span>
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight mt-2 text-white">
              Fitness Habit Tracker
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              Predictive skip-risk intelligence, behavioral factor attribution, and adaptive habit nudges.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => router.push("/dashboard")}
              className="rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-medium hover:bg-slate-800 transition"
            >
              Dashboard
            </button>
            <button
              onClick={() => router.push("/workout")}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold hover:bg-indigo-500 shadow-md shadow-indigo-600/30 transition"
            >
              + Start Workout
            </button>
            <button
              onClick={() => router.push("/buddy")}
              className="rounded-lg border border-teal-600/50 bg-teal-950/40 px-4 py-2 text-sm font-medium text-teal-300 hover:bg-teal-900/60 transition"
            >
              Gym Buddy
            </button>
            <button
              onClick={() => router.push("/nutrition")}
              className="rounded-lg border border-emerald-600/50 bg-emerald-950/40 px-4 py-2 text-sm font-medium text-emerald-300 hover:bg-emerald-900/60 transition"
            >
              Nutrition
            </button>
          </div>
        </header>

        {/* Cold Start Banner */}
        {isColdStart && (
          <div className="rounded-2xl border border-indigo-900/80 bg-gradient-to-r from-indigo-950/60 via-slate-900 to-purple-950/60 p-6 shadow-xl">
            <div className="flex items-start gap-4">
              <div className="rounded-xl bg-indigo-600/20 p-3 text-indigo-400 border border-indigo-500/30">
                <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="space-y-2">
                <h3 className="text-lg font-bold text-white">Cold-Start Habit Intelligence Active</h3>
                <p className="text-sm text-slate-300 leading-relaxed">
                  You have logged <strong className="text-indigo-300">{habitStatus?.total_sessions_logged ?? 0}</strong> completed workout session(s).
                  Our behavioral scikit-learn model requires a minimum of <strong className="text-indigo-300">3 completed sessions</strong> to establish a personalized baseline, calculate skip risk probabilities, and isolate behavioral attributions.
                </p>
                <p className="text-xs text-indigo-300 italic pt-1">
                  Keep logging your workouts! Complete {3 - (habitStatus?.total_sessions_logged ?? 0)} more session(s) to activate predictions.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Skip Risk Gauge & Adaptive Nudge Section */}
        <section className="grid gap-6 md:grid-cols-3">
          
          {/* Risk Gauge Card */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 flex flex-col justify-between shadow-lg">
            <div>
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Upcoming Skip Risk</h3>
                <span className={`rounded-full border px-3 py-0.5 text-xs font-bold ${getRiskBadgeColor(habitStatus?.risk_level || "insufficient_data")}`}>
                  {habitStatus?.risk_level.toUpperCase()}
                </span>
              </div>

              <div className="my-6 flex flex-col items-center justify-center">
                {skipProbPercent !== null ? (
                  <div className="relative flex items-center justify-center">
                    <div className="text-5xl font-black tracking-tight text-white">
                      {skipProbPercent}<span className="text-2xl text-slate-400">%</span>
                    </div>
                  </div>
                ) : (
                  <div className="text-3xl font-bold text-slate-500 py-4">N/A</div>
                )}
                <p className="text-xs text-slate-400 mt-2 text-center">
                  Predicted Skip Probability
                </p>
              </div>
            </div>

            <p className="text-xs text-slate-300 border-t border-slate-800 pt-4 leading-relaxed">
              {habitStatus?.risk_explanation}
            </p>
          </div>

          {/* Adaptive Nudge Card */}
          <div className="md:col-span-2 rounded-2xl border border-indigo-900/50 bg-gradient-to-br from-slate-900 via-slate-900 to-indigo-950/40 p-6 flex flex-col justify-between shadow-lg">
            <div>
              <div className="flex items-center gap-2 text-indigo-400 mb-3">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                <h3 className="text-sm font-bold uppercase tracking-wider text-indigo-300">Adaptive Behavioral Nudge</h3>
              </div>
              <p className="text-base font-medium text-slate-100 leading-relaxed mt-2">
                "{habitStatus?.adaptive_nudge}"
              </p>
            </div>

            {/* Optimal Schedule Box */}
            <div className="mt-6 rounded-xl border border-slate-800 bg-slate-950/70 p-4 flex items-center gap-3">
              <div className="rounded-lg bg-teal-500/10 p-2.5 text-teal-400 border border-teal-500/20">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <div>
                <div className="text-xs font-semibold text-teal-300 uppercase tracking-wider">Historical Schedule Intelligence</div>
                <div className="text-xs text-slate-300 mt-0.5">{habitStatus?.recommended_schedule}</div>
              </div>
            </div>
          </div>

        </section>

        {/* Behavioral Factor Attributions */}
        <section className="space-y-4">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <span>Behavioral Factor Signals</span>
            <span className="text-xs font-normal text-slate-400">(Non-causal attribution)</span>
          </h2>

          <div className="grid gap-4 md:grid-cols-3">
            {habitStatus?.behavioral_factors.map((factor, idx) => (
              <div key={idx} className="rounded-xl border border-slate-800 bg-slate-900 p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-indigo-400">{factor.feature_name}</span>
                  <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md ${
                    factor.signal_direction === "decreases_risk" 
                      ? "bg-emerald-950 text-emerald-300 border border-emerald-800" 
                      : "bg-rose-950 text-rose-300 border border-rose-800"
                  }`}>
                    {factor.signal_direction === "decreases_risk" ? "Protective" : "Elevates Risk"}
                  </span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {factor.description}
                </p>
                <div className="text-[11px] text-slate-500 font-medium">
                  Impact: <span className="text-slate-300 capitalize">{factor.impact_level}</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* 8 Feature Telemetry Grid */}
        {habitStatus?.features && (
          <section className="space-y-4">
            <h2 className="text-xl font-bold text-white">Extracted Telemetry Vector (8 Features)</h2>
            <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-4">
              
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                <div className="text-xs text-slate-400">Days Since Last Workout</div>
                <div className="text-2xl font-bold text-white mt-1">{habitStatus.features.days_since_last_workout} <span className="text-xs font-normal text-slate-400">days</span></div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                <div className="text-xs text-slate-400">Past 7 Days Frequency</div>
                <div className="text-2xl font-bold text-white mt-1">{habitStatus.features.workout_frequency_7d} <span className="text-xs font-normal text-slate-400">sessions</span></div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                <div className="text-xs text-slate-400">Past 30 Days Frequency</div>
                <div className="text-2xl font-bold text-white mt-1">{habitStatus.features.workout_frequency_30d} <span className="text-xs font-normal text-slate-400">sessions</span></div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                <div className="text-xs text-slate-400">Avg Weekly Workouts</div>
                <div className="text-2xl font-bold text-white mt-1">{habitStatus.features.avg_weekly_workouts} <span className="text-xs font-normal text-slate-400">/ week</span></div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                <div className="text-xs text-slate-400">Consistency Score</div>
                <div className="text-2xl font-bold text-white mt-1">{Math.round(habitStatus.features.consistency_score * 100)}%</div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                <div className="text-xs text-slate-400">Preferred Weekday Ratio</div>
                <div className="text-2xl font-bold text-white mt-1">{Math.round(habitStatus.features.preferred_weekday_ratio * 100)}%</div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                <div className="text-xs text-slate-400">Max Gap (Past 30d)</div>
                <div className="text-2xl font-bold text-white mt-1">{habitStatus.features.max_gap_days_30d} <span className="text-xs font-normal text-slate-400">days</span></div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                <div className="text-xs text-slate-400">Form Score Trend Delta</div>
                <div className="text-2xl font-bold text-white mt-1">{habitStatus.features.form_score_trend_delta > 0 ? `+${habitStatus.features.form_score_trend_delta}` : habitStatus.features.form_score_trend_delta}</div>
              </div>

            </div>
          </section>
        )}

        {/* Historical Predictions Timeline Table */}
        <section className="space-y-4 pt-4">
          <h2 className="text-xl font-bold text-white">Historical Telemetry & Prediction Logs</h2>
          {history.length === 0 ? (
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 text-center text-slate-400 text-sm">
              No historical prediction logs stored yet.
            </div>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] tracking-wider">
                  <tr>
                    <th className="px-4 py-3">Date</th>
                    <th className="px-4 py-3">Skip Probability</th>
                    <th className="px-4 py-3">Risk Level</th>
                    <th className="px-4 py-3">Primary Factor</th>
                    <th className="px-4 py-3">Nudge Text</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {history.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-800/40">
                      <td className="px-4 py-3 font-mono whitespace-nowrap">
                        {new Date(item.prediction_date).toLocaleDateString()} {new Date(item.prediction_date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td className="px-4 py-3 font-bold">
                        {item.skip_probability !== null ? `${Math.round(item.skip_probability * 100)}%` : "N/A"}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${getRiskBadgeColor(item.risk_level)}`}>
                          {item.risk_level}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-indigo-300">
                        {item.primary_factor || "N/A"}
                      </td>
                      <td className="px-4 py-3 max-w-md truncate text-slate-400">
                        {item.nudge_text || "N/A"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

      </div>
    </main>
  );
}

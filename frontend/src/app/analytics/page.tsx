"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE_URL } from "@/api/config";

type TimeWindow = "7_days" | "14_days" | "30_days";

export default function AnalyticsPage() {
  const router = useRouter();
  const [timeWindow, setTimeWindow] = useState<TimeWindow>("7_days");
  const [activeTab, setActiveTab] = useState<"overview" | "workouts" | "nutrition" | "habits" | "iot">("overview");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [overview, setOverview] = useState<any>(null);
  const [workouts, setWorkouts] = useState<any>(null);
  const [nutrition, setNutrition] = useState<any>(null);
  const [habits, setHabits] = useState<any>(null);
  const [iot, setIot] = useState<any>(null);

  useEffect(() => {
    async function loadAnalytics() {
      const token = localStorage.getItem("access_token");
      if (!token) {
        router.push("/login");
        return;
      }

      setLoading(true);
      setError("");

      try {
        const headers = { Authorization: `Bearer ${token}` };

        const [ovRes, wkRes, nuRes, hbRes, ioRes] = await Promise.all([
          fetch(`${API_BASE_URL}/analytics/overview?time_window=${timeWindow}`, { headers }),
          fetch(`${API_BASE_URL}/analytics/workouts?time_window=${timeWindow}`, { headers }),
          fetch(`${API_BASE_URL}/analytics/nutrition?time_window=${timeWindow}`, { headers }),
          fetch(`${API_BASE_URL}/analytics/habits?time_window=${timeWindow}`, { headers }),
          fetch(`${API_BASE_URL}/analytics/iot?time_window=${timeWindow}`, { headers }),
        ]);

        if (ovRes.status === 401 || wkRes.status === 401) {
          localStorage.removeItem("access_token");
          router.push("/login");
          return;
        }

        const ovData = await ovRes.json();
        const wkData = await wkRes.json();
        const nuData = await nuRes.json();
        const hbData = await hbRes.json();
        const ioData = await ioRes.json();

        setOverview(ovData);
        setWorkouts(wkData);
        setNutrition(nuData);
        setHabits(hbData);
        setIot(ioData);
      } catch (err: any) {
        setError(err.message || "Failed to load analytics dashboard data.");
      } finally {
        setLoading(false);
      }
    }

    loadAnalytics();
  }, [router, timeWindow]);

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-950 text-slate-100 p-8 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-slate-400 text-sm font-medium">Loading Multi-Domain Analytics...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-8">
      {/* Header Bar */}
      <header className="mx-auto max-w-7xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-400 via-pink-400 to-indigo-400 bg-clip-text text-transparent">
              Analytics & Intelligence Dashboard
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-950 text-purple-300 border border-purple-800">
              Advanced Analytics
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Grounded multi-domain progress tracking across Workouts, Nutrition, Behavioral Habits & IoT Smart Gym
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Time Window Selector */}
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5">
            <span className="text-xs text-slate-400 font-medium">Window:</span>
            <select
              value={timeWindow}
              onChange={(e) => setTimeWindow(e.target.value as TimeWindow)}
              className="bg-transparent text-sm font-semibold text-purple-300 focus:outline-none cursor-pointer"
            >
              <option value="7_days" className="bg-slate-900 text-slate-100">Last 7 Days</option>
              <option value="14_days" className="bg-slate-900 text-slate-100">Last 14 Days</option>
              <option value="30_days" className="bg-slate-900 text-slate-100">Last 30 Days</option>
            </select>
          </div>

          <button
            onClick={() => router.push("/dashboard")}
            className="rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-medium hover:bg-slate-800 transition"
          >
            ← Back to Dashboard
          </button>
        </div>
      </header>

      {error && (
        <div className="mx-auto max-w-7xl mt-6 rounded-xl border border-red-500/40 bg-red-950/20 p-4 text-red-300 text-sm">
          ⚠️ {error}
        </div>
      )}

      {/* Tabs Navigation */}
      <div className="mx-auto max-w-7xl mt-6 flex flex-wrap gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab("overview")}
          className={`px-4 py-2 text-sm font-medium rounded-t-lg transition ${
            activeTab === "overview"
              ? "bg-purple-950/60 text-purple-300 border-b-2 border-purple-500"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          📊 Multi-Domain Overview
        </button>
        <button
          onClick={() => setActiveTab("workouts")}
          className={`px-4 py-2 text-sm font-medium rounded-t-lg transition ${
            activeTab === "workouts"
              ? "bg-blue-950/60 text-blue-300 border-b-2 border-blue-500"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          🏋️ Workout Performance
        </button>
        <button
          onClick={() => setActiveTab("nutrition")}
          className={`px-4 py-2 text-sm font-medium rounded-t-lg transition ${
            activeTab === "nutrition"
              ? "bg-emerald-950/60 text-emerald-300 border-b-2 border-emerald-500"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          🥗 Nutrition & Compliance
        </button>
        <button
          onClick={() => setActiveTab("habits")}
          className={`px-4 py-2 text-sm font-medium rounded-t-lg transition ${
            activeTab === "habits"
              ? "bg-indigo-950/60 text-indigo-300 border-b-2 border-indigo-500"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          📈 Habit & Skip Risk
        </button>
        <button
          onClick={() => setActiveTab("iot")}
          className={`px-4 py-2 text-sm font-medium rounded-t-lg transition ${
            activeTab === "iot"
              ? "bg-cyan-950/60 text-cyan-300 border-b-2 border-cyan-500"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          ⚡ Smart Gym & IoT
        </button>
      </div>

      {/* TAB CONTENT: 1. OVERVIEW */}
      {activeTab === "overview" && overview && (
        <section className="mx-auto max-w-7xl mt-6 space-y-6">
          {/* Summary Metric Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Card 1: User Profile */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-2">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">User Profile</span>
              <p className="text-xl font-bold text-slate-100">{overview.user_profile?.name}</p>
              <div className="flex justify-between text-xs text-slate-300 pt-2 border-t border-slate-800">
                <span>Goal: <strong className="text-purple-300 uppercase">{overview.user_profile?.fitness_goal}</strong></span>
                <span>BMI: <strong className="text-purple-300">{overview.user_profile?.bmi || "N/A"}</strong></span>
              </div>
            </div>

            {/* Card 2: Workout Summary */}
            <div className="rounded-xl border border-blue-900/50 bg-blue-950/20 p-5 space-y-2">
              <span className="text-xs font-semibold text-blue-400 uppercase tracking-wider">Workouts ({timeWindow})</span>
              <p className="text-2xl font-bold text-blue-200">
                {overview.workout_summary?.total_workouts} <span className="text-sm font-normal text-slate-400">sessions</span>
              </p>
              <div className="flex justify-between text-xs text-slate-300 pt-2 border-t border-blue-900/40">
                <span>Avg Score: <strong className="text-blue-300">{overview.workout_summary?.avg_performance_score ? `${overview.workout_summary.avg_performance_score}/100` : "No data"}</strong></span>
                <span>Trend: <strong className="text-blue-300 capitalize">{overview.workout_summary?.performance_trend || "N/A"}</strong></span>
              </div>
            </div>

            {/* Card 3: Nutrition Summary */}
            <div className="rounded-xl border border-emerald-900/50 bg-emerald-950/20 p-5 space-y-2">
              <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Nutrition ({timeWindow})</span>
              <p className="text-2xl font-bold text-emerald-200">
                {overview.nutrition_summary?.avg_daily_calories ? `${overview.nutrition_summary.avg_daily_calories} kcal` : "No logs"}
              </p>
              <div className="flex justify-between text-xs text-slate-300 pt-2 border-t border-emerald-900/40">
                <span>Target: <strong className="text-emerald-300">{overview.nutrition_summary?.target_calories} kcal</strong></span>
                <span>Compliance: <strong className="text-emerald-300">{overview.nutrition_summary?.calorie_compliance_pct ? `${overview.nutrition_summary.calorie_compliance_pct}%` : "N/A"}</strong></span>
              </div>
            </div>

            {/* Card 4: Habit & IoT Summary */}
            <div className="rounded-xl border border-purple-900/50 bg-purple-950/20 p-5 space-y-2">
              <span className="text-xs font-semibold text-purple-400 uppercase tracking-wider">Habit & IoT Status</span>
              <p className="text-lg font-bold text-purple-200 capitalize">
                Risk: {overview.habit_summary?.risk_level || "Unknown"}
              </p>
              <div className="flex justify-between text-xs text-slate-300 pt-2 border-t border-purple-900/40">
                <span>Consistency: <strong className="text-purple-300">{overview.habit_summary?.consistency_rate_pct ? `${overview.habit_summary.consistency_rate_pct}%` : "0%"}</strong></span>
                <span>IoT Devices: <strong className="text-purple-300">{overview.iot_summary?.total_devices || 0}</strong></span>
              </div>
            </div>
          </div>

          {/* Cross-Domain Observational Insights Section */}
          <div className="rounded-2xl border border-purple-900/40 bg-slate-900/50 p-6 space-y-4">
            <h2 className="text-lg font-semibold text-purple-300 flex items-center gap-2">
              <span>🧠</span> Cross-Domain Observational Insights
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {overview.cross_domain_insights?.map((item: any, idx: number) => (
                <div key={idx} className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-1">
                  <div className="flex items-center justify-between text-xs font-semibold text-purple-400">
                    <span>{item.domain}</span>
                    <span className="text-slate-500 font-normal">{item.note}</span>
                  </div>
                  <h4 className="text-sm font-bold text-slate-100">{item.title}</h4>
                  <p className="text-xs text-slate-300">{item.message}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* TAB CONTENT: 2. WORKOUT PERFORMANCE */}
      {activeTab === "workouts" && workouts && (
        <section className="mx-auto max-w-7xl mt-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="rounded-xl border border-blue-900/40 bg-slate-900 p-5 space-y-1">
              <span className="text-xs text-slate-400 uppercase">Total Sessions</span>
              <p className="text-3xl font-bold text-blue-400">{workouts.total_workouts}</p>
              <p className="text-xs text-slate-400">{workouts.total_duration_minutes} total minutes logged</p>
            </div>
            <div className="rounded-xl border border-blue-900/40 bg-slate-900 p-5 space-y-1">
              <span className="text-xs text-slate-400 uppercase">Average Score</span>
              <p className="text-3xl font-bold text-blue-400">
                {workouts.avg_performance_score ? `${workouts.avg_performance_score}/100` : "N/A"}
              </p>
              <p className="text-xs text-slate-400">Based on computer vision pose analysis</p>
            </div>
            <div className="rounded-xl border border-blue-900/40 bg-slate-900 p-5 space-y-1">
              <span className="text-xs text-slate-400 uppercase">Performance Trend</span>
              <p className="text-2xl font-bold text-emerald-400 capitalize">{workouts.performance_trend}</p>
              <p className="text-xs text-slate-400">Evaluated across selected window</p>
            </div>
          </div>

          {!workouts.has_data ? (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-8 text-center text-slate-400">
              ℹ️ No workout sessions recorded in the selected {timeWindow} window. Complete a workout to view performance breakdown.
            </div>
          ) : (
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 space-y-4">
              <h3 className="text-md font-bold text-slate-200">Recent Session History</h3>
              <div className="space-y-2">
                {workouts.session_history?.map((s: any) => (
                  <div key={s.session_id} className="flex items-center justify-between p-3 rounded-lg border border-slate-800 bg-slate-950 text-sm">
                    <div>
                      <p className="font-semibold text-slate-100">{s.date}</p>
                      <p className="text-xs text-slate-400">Duration: {s.duration_minutes} mins</p>
                    </div>
                    <div className="text-right">
                      <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-blue-950 text-blue-300 border border-blue-800">
                        Score: {s.performance_score || "N/A"}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {/* TAB CONTENT: 3. NUTRITION */}
      {activeTab === "nutrition" && nutrition && (
        <section className="mx-auto max-w-7xl mt-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="rounded-xl border border-emerald-900/40 bg-slate-900 p-5 space-y-1">
              <span className="text-xs text-slate-400 uppercase">Daily Caloric Target</span>
              <p className="text-3xl font-bold text-emerald-400">{nutrition.target?.calories_target} kcal</p>
              <p className="text-xs text-slate-400">Protein target: {nutrition.target?.protein_grams}g</p>
            </div>
            <div className="rounded-xl border border-emerald-900/40 bg-slate-900 p-5 space-y-1">
              <span className="text-xs text-slate-400 uppercase">Avg Daily Intake</span>
              <p className="text-3xl font-bold text-emerald-400">
                {nutrition.average_daily_intake?.avg_calories ? `${nutrition.average_daily_intake.avg_calories} kcal` : "N/A"}
              </p>
              <p className="text-xs text-slate-400">Avg Protein: {nutrition.average_daily_intake?.avg_protein_g || 0}g</p>
            </div>
            <div className="rounded-xl border border-emerald-900/40 bg-slate-900 p-5 space-y-1">
              <span className="text-xs text-slate-400 uppercase">Calorie Compliance</span>
              <p className="text-3xl font-bold text-emerald-400">
                {nutrition.compliance?.calorie_compliance_pct !== null ? `${nutrition.compliance.calorie_compliance_pct}%` : "N/A"}
              </p>
              <p className="text-xs text-slate-400">Target tolerance: ±15%</p>
            </div>
          </div>

          {!nutrition.has_data ? (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-8 text-center text-slate-400">
              ℹ️ Insufficient nutrition logs in the selected {timeWindow} window. Log your meals to track daily compliance.
            </div>
          ) : (
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 space-y-4">
              <h3 className="text-md font-bold text-slate-200">Daily Intake Timeline</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {nutrition.daily_trends?.map((d: any) => (
                  <div key={d.date} className="p-3 rounded-lg border border-slate-800 bg-slate-950 text-xs space-y-1">
                    <div className="flex justify-between items-center font-semibold text-slate-200">
                      <span>{d.date}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${d.is_compliant ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' : 'bg-slate-800 text-slate-400'}`}>
                        {d.is_compliant ? 'Compliant' : 'Off Target'}
                      </span>
                    </div>
                    <p className="text-slate-300 font-bold text-sm">{d.calories} kcal</p>
                    <p className="text-slate-400">P: {d.protein_g}g | C: {d.carbs_g}g | F: {d.fat_g}g</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {/* TAB CONTENT: 4. HABITS */}
      {activeTab === "habits" && habits && (
        <section className="mx-auto max-w-7xl mt-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="rounded-xl border border-indigo-900/40 bg-slate-900 p-5 space-y-1">
              <span className="text-xs text-slate-400 uppercase">Habit Risk Level</span>
              <p className="text-3xl font-bold text-indigo-400 capitalize">{habits.current_status?.risk_level || "Normal"}</p>
              <p className="text-xs text-slate-400">Skip prob: {habits.current_status?.skip_probability !== null ? `${(habits.current_status.skip_probability * 100).toFixed(1)}%` : "N/A"}</p>
            </div>
            <div className="rounded-xl border border-indigo-900/40 bg-slate-900 p-5 space-y-1">
              <span className="text-xs text-slate-400 uppercase">Consistency Rate</span>
              <p className="text-3xl font-bold text-indigo-400">{habits.consistency?.consistency_rate_pct}%</p>
              <p className="text-xs text-slate-400">Target: {habits.consistency?.target_days_per_week} days/week</p>
            </div>
            <div className="rounded-xl border border-indigo-900/40 bg-slate-900 p-5 space-y-1">
              <span className="text-xs text-slate-400 uppercase">Workouts Completed</span>
              <p className="text-3xl font-bold text-indigo-400">
                {habits.consistency?.actual_workouts_in_window} / {habits.consistency?.expected_workouts_in_window}
              </p>
              <p className="text-xs text-slate-400">Actual vs Expected in window</p>
            </div>
          </div>

          <div className="rounded-2xl border border-indigo-900/40 bg-slate-900 p-6 space-y-3">
            <h3 className="text-md font-bold text-indigo-300">Adaptive Behavioral Guidance</h3>
            <p className="text-sm text-slate-200">{habits.current_status?.recommendation}</p>
          </div>
        </section>
      )}

      {/* TAB CONTENT: 5. SMART GYM IOT */}
      {activeTab === "iot" && iot && (
        <section className="mx-auto max-w-7xl mt-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="rounded-xl border border-cyan-900/40 bg-slate-900 p-5 space-y-1">
              <span className="text-xs text-slate-400 uppercase">Connected Devices</span>
              <p className="text-3xl font-bold text-cyan-400">{iot.device_counts?.total_devices}</p>
              <p className="text-xs text-slate-400">{iot.device_counts?.simulated_devices} Simulated Demo Devices</p>
            </div>
            <div className="rounded-xl border border-cyan-900/40 bg-slate-900 p-5 space-y-1">
              <span className="text-xs text-slate-400 uppercase">Avg Set Intensity</span>
              <p className="text-3xl font-bold text-cyan-400">
                {iot.telemetry_averages?.avg_intensity ? `${iot.telemetry_averages.avg_intensity}%` : "N/A"}
              </p>
              <p className="text-xs text-slate-400">Avg Resistance: {iot.telemetry_averages?.avg_resistance_kg || 0} kg</p>
            </div>
            <div className="rounded-xl border border-cyan-900/40 bg-slate-900 p-5 space-y-1">
              <span className="text-xs text-slate-400 uppercase">Avg Heart Rate</span>
              <p className="text-3xl font-bold text-cyan-400">
                {iot.telemetry_averages?.avg_heart_rate ? `${iot.telemetry_averages.avg_heart_rate} BPM` : "N/A"}
              </p>
              <p className="text-xs text-slate-400">{iot.telemetry_averages?.total_telemetry_records || 0} telemetry records</p>
            </div>
          </div>

          {!iot.has_data ? (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-8 text-center text-slate-400">
              ℹ️ No connected Smart Gym devices or telemetry recorded in {timeWindow}. Visit the Smart Gym IoT page to connect devices or generate simulation telemetry.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {iot.device_breakdown?.map((dev: any) => (
                <div key={dev.device_id} className="rounded-xl border border-cyan-950 bg-slate-900 p-4 space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-sm text-slate-100">{dev.device_name}</span>
                    {dev.is_simulated && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950 text-amber-300 border border-amber-800">
                        Simulation Mode
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-400 capitalize">Category: {dev.equipment_category}</p>
                  <div className="flex justify-between text-xs text-slate-300 pt-2 border-t border-slate-800">
                    <span>Intensity: <strong className="text-cyan-300">{dev.avg_intensity ? `${dev.avg_intensity}%` : "N/A"}</strong></span>
                    <span>Resistance: <strong className="text-cyan-300">{dev.avg_resistance_kg} kg</strong></span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </main>
  );
}

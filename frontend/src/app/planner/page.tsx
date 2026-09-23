"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE_URL } from "@/api/config";

interface GymItem {
  id: number;
  name: string;
  address: string;
  city: string;
  price_category: string;
  rating: number;
  opening_hours: string;
  facilities: string[];
  equipment: string[];
  supported_workout_types: string[];
  is_verified_sample: boolean;
}

interface GymRecommendation {
  gym: GymItem;
  suitability_score: number;
  match_category: string;
  match_reasons: string[];
}

interface ExerciseItem {
  name: string;
  sets: number;
  reps_or_duration: string;
  target_muscle: string;
  technique_cue?: string;
}

interface WorkoutPlanItem {
  id: number;
  day_of_week: string;
  day_title: string;
  is_rest_day: boolean;
  target_muscle_groups?: string;
  exercises: ExerciseItem[];
  warmup_notes?: string;
}

interface WorkoutPlan {
  id: number;
  user_id: number;
  plan_name: string;
  fitness_goal: string;
  target_split: string;
  days_per_week: number;
  habit_adapted: boolean;
  performance_adapted: boolean;
  adaptation_notes?: string;
  items: WorkoutPlanItem[];
  created_at: string;
}

export default function PlannerPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"gyms" | "planner">("gyms");
  
  // Gyms state
  const [recommendations, setRecommendations] = useState<GymRecommendation[]>([]);
  const [gymSearch, setGymSearch] = useState("");
  const [userGoal, setUserGoal] = useState("");
  
  // Planner state
  const [activePlan, setActivePlan] = useState<WorkoutPlan | null>(null);
  const [selectedGoal, setSelectedGoal] = useState<string>("hypertrophy");
  const [generating, setGenerating] = useState(false);

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
        const [recRes, planRes] = await Promise.all([
          fetch(`${API_BASE_URL}/gyms/recommendations?limit=6`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch(`${API_BASE_URL}/planner/latest`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
        ]);

        if (recRes.status === 401 || planRes.status === 401) {
          localStorage.removeItem("access_token");
          router.push("/login");
          return;
        }

        if (recRes.ok) {
          const recData = await recRes.json();
          setRecommendations(recData.recommendations || []);
          setUserGoal(recData.user_goal || "maintenance");
          if (recData.user_goal) {
            setSelectedGoal(recData.user_goal);
          }
        }

        if (planRes.ok) {
          const planData = await planRes.json();
          setActivePlan(planData);
        }
      } catch (err) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Failed to communicate with recommendation server.");
        }
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [router]);

  async function handleGeneratePlan() {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    setGenerating(true);
    try {
      const res = await fetch(`${API_BASE_URL}/planner/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          fitness_goal: selectedGoal,
        }),
      });

      if (res.ok) {
        const newPlan = await res.json();
        setActivePlan(newPlan);
      }
    } catch (err) {
      console.error("Plan generation error", err);
    } finally {
      setGenerating(false);
    }
  }

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-white">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
          <p className="text-slate-400 text-sm">Matching gym suitability & generating weekly planner...</p>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-white p-6">
        <div className="max-w-md rounded-2xl border border-red-900 bg-slate-900 p-8 text-center shadow-xl">
          <h1 className="text-2xl font-bold text-red-400">Service Error</h1>
          <p className="mt-3 text-slate-300 text-sm">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-6 rounded-lg bg-red-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-red-500 transition"
          >
            Retry
          </button>
        </div>
      </main>
    );
  }

  const filteredRecommendations = recommendations.filter((item) => {
    if (!gymSearch) return true;
    const search = gymSearch.toLowerCase();
    return (
      item.gym.name.toLowerCase().includes(search) ||
      item.gym.address.toLowerCase().includes(search) ||
      item.gym.equipment.some((e) => e.toLowerCase().includes(search))
    );
  });

  return (
    <main className="min-h-screen bg-slate-950 text-white p-6 md:p-10">
      <div className="mx-auto max-w-6xl space-y-8">
        
        {/* Header Bar */}
        <header className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-indigo-900/60 border border-indigo-500 px-3 py-0.5 text-xs font-semibold text-indigo-300">
                Phase 7 — Recommender & Planner
              </span>
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight mt-2 text-white">
              Gym Recommender & Workout Planner
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              Personalized gym suitability scoring and adaptive weekly workout schedule design.
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
              onClick={() => router.push("/habit")}
              className="rounded-lg border border-indigo-600/50 bg-indigo-950/40 px-4 py-2 text-sm font-medium text-indigo-300 hover:bg-indigo-900/60 transition"
            >
              Habit Tracker
            </button>
            <button
              onClick={() => router.push("/buddy")}
              className="rounded-lg border border-teal-600/50 bg-teal-950/40 px-4 py-2 text-sm font-medium text-teal-300 hover:bg-teal-900/60 transition"
            >
              Gym Buddy
            </button>
          </div>
        </header>

        {/* Tab Switcher */}
        <div className="flex items-center gap-4 border-b border-slate-800 pb-2">
          <button
            onClick={() => setActiveTab("gyms")}
            className={`px-5 py-2.5 text-sm font-bold rounded-xl transition ${
              activeTab === "gyms"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/30"
                : "bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-white"
            }`}
          >
            🏋️ Gym Recommender ({filteredRecommendations.length})
          </button>

          <button
            onClick={() => setActiveTab("planner")}
            className={`px-5 py-2.5 text-sm font-bold rounded-xl transition ${
              activeTab === "planner"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/30"
                : "bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-white"
            }`}
          >
            📅 Weekly Workout Planner
          </button>
        </div>

        {/* TAB 1: GYM RECOMMENDER */}
        {activeTab === "gyms" && (
          <div className="space-y-6">
            
            {/* Search Filter & Context Bar */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 rounded-2xl border border-slate-800 bg-slate-900 p-4">
              <div className="w-full sm:w-80">
                <input
                  type="text"
                  placeholder="Search by equipment, location, or facility..."
                  value={gymSearch}
                  onChange={(e) => setGymSearch(e.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-2 text-sm text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div className="text-xs text-slate-400">
                Personalized for goal: <strong className="text-indigo-400 capitalize">{userGoal}</strong>
              </div>
            </div>

            {/* Gym Cards Grid */}
            <div className="grid gap-6 md:grid-cols-2">
              {filteredRecommendations.map((rec) => (
                <div
                  key={rec.gym.id}
                  className="rounded-2xl border border-slate-800 bg-slate-900 p-6 flex flex-col justify-between shadow-xl space-y-4 hover:border-slate-700 transition"
                >
                  <div>
                    {/* Header line: Gym Name & Suitability Badge */}
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="text-xl font-bold text-white">{rec.gym.name}</h3>
                        <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                          📍 {rec.gym.address}, {rec.gym.city}
                        </p>
                      </div>

                      <div className="flex flex-col items-end">
                        <span className="rounded-full border border-indigo-500/50 bg-indigo-950 px-3 py-1 text-xs font-bold text-indigo-300">
                          {rec.suitability_score}% Suitability
                        </span>
                        <span className="text-[10px] text-slate-400 mt-1">{rec.match_category}</span>
                      </div>
                    </div>

                    {/* Metadata line: Rating & Price */}
                    <div className="flex items-center gap-4 my-3 text-xs text-slate-300 border-y border-slate-800 py-2.5">
                      <div className="flex items-center gap-1 text-amber-400 font-bold">
                        ★ {rec.gym.rating.toFixed(1)} / 5.0
                      </div>
                      <div>
                        Price Tier: <span className="font-semibold capitalize text-indigo-300">{rec.gym.price_category.replace("_", " ")}</span>
                      </div>
                      <div>
                        Hours: <span className="text-slate-400">{rec.gym.opening_hours}</span>
                      </div>
                    </div>

                    {/* Match Reasons List */}
                    <div className="space-y-1.5 my-3">
                      <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Match Explanations</div>
                      <ul className="space-y-1 text-xs text-slate-300">
                        {rec.match_reasons.map((reason, idx) => (
                          <li key={idx} className="flex items-start gap-1.5">
                            <span className="text-indigo-400">✓</span>
                            <span>{reason}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* Equipment Tags */}
                    <div className="space-y-1.5 pt-2">
                      <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Available Infrastructure</div>
                      <div className="flex flex-wrap gap-1.5">
                        {rec.gym.equipment.map((eq, idx) => (
                          <span key={idx} className="rounded-md bg-slate-950 border border-slate-800 px-2 py-0.5 text-[11px] text-slate-300">
                            {eq}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="text-[10px] text-slate-500 italic pt-2 border-t border-slate-800/60">
                    Sample Demo Gym Data • Grounded Recommendation Algorithm
                  </div>
                </div>
              ))}
            </div>

          </div>
        )}

        {/* TAB 2: WEEKLY WORKOUT PLANNER */}
        {activeTab === "planner" && (
          <div className="space-y-6">
            
            {/* Control Bar */}
            <div className="flex flex-col md:flex-row items-center justify-between gap-4 rounded-2xl border border-slate-800 bg-slate-900 p-6">
              <div>
                <h3 className="text-lg font-bold text-white">Interactive 7-Day Workout Planner</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Dynamically structured for your goal with Phase 3 posture & Phase 6 habit adaptivity.
                </p>
              </div>

              <div className="flex items-center gap-3 w-full md:w-auto">
                <select
                  value={selectedGoal}
                  onChange={(e) => setSelectedGoal(e.target.value)}
                  className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-indigo-500 focus:outline-none"
                >
                  <option value="hypertrophy">Hypertrophy (Muscle Gain)</option>
                  <option value="strength">Strength (Power & Heavy Loading)</option>
                  <option value="weight_loss">Weight Loss & HIIT</option>
                  <option value="endurance">Endurance & Conditioning</option>
                  <option value="maintenance">General Maintenance</option>
                </select>

                <button
                  onClick={handleGeneratePlan}
                  disabled={generating}
                  className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white hover:bg-indigo-500 shadow-md shadow-indigo-600/30 transition disabled:opacity-50"
                >
                  {generating ? "Generating..." : "Generate New Plan"}
                </button>
              </div>
            </div>

            {/* Plan Info Banner */}
            {activePlan && (
              <div className="rounded-2xl border border-indigo-900/50 bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 p-6 shadow-xl space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <span className="rounded-full bg-indigo-900/60 border border-indigo-500 px-3 py-0.5 text-xs font-semibold text-indigo-300">
                      Active Weekly Plan
                    </span>
                    <h2 className="text-2xl font-bold text-white mt-1">{activePlan.plan_name}</h2>
                    <p className="text-xs text-slate-300 mt-1">
                      Target Split: <strong className="text-indigo-300">{activePlan.target_split}</strong> • {activePlan.days_per_week} Training Days / Week
                    </p>
                  </div>

                  <div className="flex gap-2">
                    {activePlan.habit_adapted && (
                      <span className="rounded-lg bg-amber-950 border border-amber-700 px-3 py-1 text-xs font-bold text-amber-300">
                        Habit Adapted
                      </span>
                    )}
                    {activePlan.performance_adapted && (
                      <span className="rounded-lg bg-teal-950 border border-teal-700 px-3 py-1 text-xs font-bold text-teal-300">
                        Performance Adapted
                      </span>
                    )}
                  </div>
                </div>

                {activePlan.adaptation_notes && (
                  <div className="text-xs text-indigo-300 bg-indigo-950/60 border border-indigo-800/60 p-3 rounded-xl leading-relaxed">
                    💡 <strong>Adaptation Cues:</strong> {activePlan.adaptation_notes}
                  </div>
                )}
              </div>
            )}

            {/* 7-Day Schedule Items */}
            {activePlan?.items && (
              <div className="grid gap-4 md:grid-cols-2">
                {activePlan.items.map((item) => (
                  <div
                    key={item.id}
                    className={`rounded-2xl border p-5 space-y-3 shadow-lg transition ${
                      item.is_rest_day
                        ? "border-slate-800/80 bg-slate-950/60"
                        : "border-slate-800 bg-slate-900"
                    }`}
                  >
                    <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                      <div>
                        <span className="text-xs font-mono font-semibold text-indigo-400 uppercase">{item.day_of_week}</span>
                        <h4 className="text-base font-bold text-white mt-0.5">{item.day_title}</h4>
                      </div>

                      <span className={`px-2.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                        item.is_rest_day
                          ? "bg-slate-800 text-slate-400"
                          : "bg-emerald-950 text-emerald-300 border border-emerald-800"
                      }`}>
                        {item.is_rest_day ? "Rest Day" : "Workout"}
                      </span>
                    </div>

                    {!item.is_rest_day ? (
                      <div className="space-y-3">
                        {item.warmup_notes && (
                          <div className="text-[11px] text-teal-300 bg-teal-950/40 border border-teal-800/50 p-2 rounded-lg">
                            ⚡ <strong>Warmup/Technique:</strong> {item.warmup_notes}
                          </div>
                        )}

                        <div className="space-y-2">
                          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Prescribed Exercises</div>
                          {item.exercises.map((ex, idx) => (
                            <div key={idx} className="rounded-xl border border-slate-800 bg-slate-950 p-3 flex flex-col justify-between gap-1">
                              <div className="flex items-center justify-between">
                                <span className="text-xs font-bold text-white">{ex.name}</span>
                                <span className="text-xs font-mono font-bold text-indigo-300">{ex.sets} sets × {ex.reps_or_duration}</span>
                              </div>
                              {ex.technique_cue && (
                                <p className="text-[11px] text-slate-400 italic">
                                  Cue: {ex.technique_cue}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500 italic py-2">
                        Focus on active recovery, hydration, foam rolling, and mobility work.
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}

          </div>
        )}

      </div>
    </main>
  );
}

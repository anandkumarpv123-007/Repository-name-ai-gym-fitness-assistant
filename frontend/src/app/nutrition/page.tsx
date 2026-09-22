"use client";

import { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { API_BASE_URL } from "@/api/config";

interface BMIResponse {
  height_cm: number;
  weight_kg: number;
  bmi: number;
  category: string;
  healthy_weight_min_kg: number;
  healthy_weight_max_kg: number;
  bmr: number;
  tdee: number;
  recommended_calories: number;
  recommended_protein_g: number;
  recommended_carbs_g: number;
  recommended_fat_g: number;
  water_liters: number;
}

interface NutritionTarget {
  id: number;
  user_id: number;
  calories_target: number;
  protein_grams: number;
  carbs_grams: number;
  fat_grams: number;
  water_liters: number;
  dietary_preference: string;
  allergies_restrictions?: string | null;
  meals_per_day: number;
}

interface FoodCatalogueItem {
  id: string;
  name: string;
  category: string;
  serving_size_g: number;
  calories_per_100g: number;
  protein_per_100g: number;
  carbs_per_100g: number;
  fat_per_100g: number;
}

interface FoodLogItem {
  id: number;
  user_id: number;
  log_date: string;
  meal_type: string;
  food_name: string;
  quantity: number;
  unit: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
}

interface DailySummary {
  date: string;
  total_calories: number;
  total_protein: number;
  total_carbs: number;
  total_fat: number;
  target_calories: number;
  target_protein: number;
  target_carbs: number;
  target_fat: number;
  water_liters: number;
  remaining_calories: number;
  calories_percentage: number;
  protein_percentage: number;
  carbs_percentage: number;
  fat_percentage: number;
  status: string;
  meal_breakdown: Record<string, FoodLogItem[]>;
}

interface MealItem {
  name: string;
  quantity: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

interface MealPlanItem {
  meal_type: string;
  meal_name: string;
  items: MealItem[];
  total_calories: number;
  total_protein_g: number;
  total_carbs_g: number;
  total_fat_g: number;
  instructions?: string;
}

interface GroceryCategory {
  category: string;
  items: string[];
}

interface DietPlan {
  id: number;
  user_id: number;
  calories_target: number;
  dietary_preference: string;
  goal: string;
  meals: MealPlanItem[];
  total_plan_calories: number;
  total_plan_protein: number;
  total_plan_carbs: number;
  total_plan_fat: number;
  grocery_list: GroceryCategory[];
  notes?: string;
  provider: string;
  disclaimer: string;
}

export default function NutritionPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"tracker" | "targets" | "dietician" | "grocery">("tracker");
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");
  const [successMsg, setSuccessMsg] = useState<string>("");

  // Core Nutrition Data
  const [bmiData, setBmiData] = useState<BMIResponse | null>(null);
  const [target, setTarget] = useState<NutritionTarget | null>(null);
  const [summary, setSummary] = useState<DailySummary | null>(null);
  const [dietPlan, setDietPlan] = useState<DietPlan | null>(null);
  const [foodsCatalogue, setFoodsCatalogue] = useState<FoodCatalogueItem[]>([]);

  // Food Logging Form State
  const [logModalOpen, setLogModalOpen] = useState<boolean>(false);
  const [foodSearch, setFoodSearch] = useState<string>("");
  const [selectedMealType, setSelectedMealType] = useState<string>("breakfast");
  const [foodName, setFoodName] = useState<string>("");
  const [quantity, setQuantity] = useState<number>(100);
  const [unit, setUnit] = useState<string>("g");
  const [calories, setCalories] = useState<number>(150);
  const [protein, setProtein] = useState<number>(10);
  const [carbs, setCarbs] = useState<number>(15);
  const [fat, setFat] = useState<number>(5);

  // Diet Plan Generation State
  const [planPref, setPlanPref] = useState<string>("standard");
  const [planAllergies, setPlanAllergies] = useState<string>("");
  const [planMealsCount, setPlanMealsCount] = useState<number>(3);
  const [generatingPlan, setGeneratingPlan] = useState<boolean>(false);

  // Grocery check state
  const [checkedItems, setCheckedItems] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
      return;
    }

    async function loadNutritionData() {
      try {
        setLoading(true);
        setError("");
        const headers = { Authorization: `Bearer ${token}` };

        // 1. Fetch Summary & Targets concurrently
        const [sumRes, targetRes, catRes] = await Promise.all([
          fetch(`${API_BASE_URL}/diet/summary`, { headers }),
          fetch(`${API_BASE_URL}/diet/target`, { headers }),
          fetch(`${API_BASE_URL}/diet/foods`),
        ]);

        if (sumRes.status === 401 || targetRes.status === 401) {
          localStorage.removeItem("access_token");
          router.push("/login");
          return;
        }

        if (sumRes.ok) {
          const sumData = await sumRes.json();
          setSummary(sumData);
        }
        if (targetRes.ok) {
          const tarData = await targetRes.json();
          setTarget(tarData);
          setPlanPref(tarData.dietary_preference || "standard");
        }
        if (catRes.ok) {
          const catData = await catRes.json();
          setFoodsCatalogue(catData);
        }

        // 2. Fetch BMI
        const bmiRes = await fetch(`${API_BASE_URL}/diet/bmi`, { headers });
        if (bmiRes.ok) {
          const bData = await bmiRes.json();
          setBmiData(bData);
        }

        // 3. Fetch latest diet plan if available
        const planRes = await fetch(`${API_BASE_URL}/diet/plan/latest`, { headers });
        if (planRes.ok) {
          const pData = await planRes.json();
          setDietPlan(pData);
        }
      } catch (err: unknown) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Failed to load nutrition data");
        }
      } finally {
        setLoading(false);
      }
    }

    loadNutritionData();
  }, [router]);

  // Handle selecting a food from catalogue
  function handleSelectCatalogueItem(item: FoodCatalogueItem) {
    setFoodName(item.name);
    setQuantity(item.serving_size_g);
    setUnit("g");
    const ratio = item.serving_size_g / 100.0;
    setCalories(Math.round(item.calories_per_100g * ratio));
    setProtein(Math.round(item.protein_per_100g * ratio * 10) / 10);
    setCarbs(Math.round(item.carbs_per_100g * ratio * 10) / 10);
    setFat(Math.round(item.fat_per_100g * ratio * 10) / 10);
  }

  // Handle quantity adjustments
  function handleQuantityChange(newQty: number) {
    setQuantity(newQty);
    // If food matches a catalogue item, recalculate
    const found = foodsCatalogue.find((f) => f.name.toLowerCase() === foodName.toLowerCase());
    if (found && newQty > 0) {
      const ratio = newQty / 100.0;
      setCalories(Math.round(found.calories_per_100g * ratio));
      setProtein(Math.round(found.protein_per_100g * ratio * 10) / 10);
      setCarbs(Math.round(found.carbs_per_100g * ratio * 10) / 10);
      setFat(Math.round(found.fat_per_100g * ratio * 10) / 10);
    }
  }

  // Log food submit
  async function handleFoodLogSubmit(e: React.FormEvent) {
    e.preventDefault();
    const token = localStorage.getItem("access_token");
    if (!token) return;

    try {
      setError("");
      const res = await fetch(`${API_BASE_URL}/diet/log`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          food_name: foodName,
          quantity: Number(quantity),
          unit: unit,
          meal_type: selectedMealType,
          calories: Number(calories),
          protein: Number(protein),
          carbs: Number(carbs),
          fat: Number(fat),
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to log food");
      }

      setSuccessMsg(`Logged ${foodName} to ${selectedMealType}!`);
      setTimeout(() => setSuccessMsg(""), 4000);
      setLogModalOpen(false);

      // Refresh daily summary
      const sumRes = await fetch(`${API_BASE_URL}/diet/summary`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (sumRes.ok) {
        setSummary(await sumRes.json());
      }
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message);
    }
  }

  // Delete food log
  async function handleDeleteFoodLog(logId: number) {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    try {
      const res = await fetch(`${API_BASE_URL}/diet/log/${logId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        // Refresh summary
        const sumRes = await fetch(`${API_BASE_URL}/diet/summary`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (sumRes.ok) {
          setSummary(await sumRes.json());
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message);
    }
  }

  // Generate AI Diet Plan
  async function handleGenerateDietPlan() {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    try {
      setGeneratingPlan(true);
      setError("");
      const res = await fetch(`${API_BASE_URL}/diet/plan`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          dietary_preference: planPref,
          allergies_restrictions: planAllergies || null,
          meals_per_day: Number(planMealsCount),
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to generate diet plan");
      }

      const planData = await res.json();
      setDietPlan(planData);
      setActiveTab("dietician");
      setSuccessMsg("Generated personalized diet plan & grocery list!");
      setTimeout(() => setSuccessMsg(""), 4000);
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message);
    } finally {
      setGeneratingPlan(false);
    }
  }

  const toggleGroceryCheck = (itemKey: string) => {
    setCheckedItems((prev) => ({ ...prev, [itemKey]: !prev[itemKey] }));
  };

  const filteredCatalogue = useMemo(() => {
    if (!foodSearch) return foodsCatalogue.slice(0, 10);
    const q = foodSearch.toLowerCase();
    return foodsCatalogue.filter((f) => f.name.toLowerCase().includes(q) || f.category.toLowerCase().includes(q));
  }, [foodSearch, foodsCatalogue]);

  return (
    <main className="min-h-screen bg-slate-950 p-4 md:p-8 text-white font-sans">
      {/* Navigation Header */}
      <header className="mx-auto flex max-w-6xl flex-col md:flex-row md:items-center justify-between border-b border-slate-800 pb-5 gap-4">
        <div>
          <div className="flex items-center gap-3">
            <span className="rounded-md bg-emerald-950 border border-emerald-700 px-2.5 py-0.5 text-xs font-bold tracking-wide text-emerald-300 uppercase">
              Phase 4 Intelligence
            </span>
            <span className="text-xs text-slate-500">Nutrition + AI Dietician</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 bg-clip-text text-transparent mt-1.5">
            Nutrition & AI Dietician
          </h1>
          <p className="text-xs md:text-sm text-slate-400 mt-1">
            Deterministic metabolic baselines, daily macronutrient tracking, and smart meal planning
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Link
            href="/dashboard"
            className="rounded-lg border border-slate-800 bg-slate-900 px-3.5 py-1.5 text-xs md:text-sm font-medium hover:bg-slate-800 transition"
          >
            Dashboard
          </Link>
          <Link
            href="/reports"
            className="rounded-lg border border-slate-800 bg-slate-900 px-3.5 py-1.5 text-xs md:text-sm font-medium hover:bg-slate-800 transition"
          >
            Weekly Intelligence
          </Link>
          <Link
            href="/workout"
            className="rounded-lg bg-blue-600 px-4 py-1.5 text-xs md:text-sm font-semibold text-white hover:bg-blue-500 shadow-md shadow-blue-600/30 transition"
          >
            + Start Workout
          </Link>
        </div>
      </header>

      {/* Notifications */}
      {error && (
        <div className="mx-auto mt-4 max-w-6xl rounded-xl border border-rose-900/80 bg-rose-950/40 p-4 text-sm text-rose-300 flex items-center justify-between">
          <span>⚠️ {error}</span>
          <button onClick={() => setError("")} className="text-rose-400 font-bold hover:text-white">✕</button>
        </div>
      )}
      {successMsg && (
        <div className="mx-auto mt-4 max-w-6xl rounded-xl border border-emerald-900/80 bg-emerald-950/40 p-4 text-sm text-emerald-300">
          ✅ {successMsg}
        </div>
      )}

      {/* Sub-Navigation Tabs */}
      <div className="mx-auto mt-6 max-w-6xl flex border-b border-slate-800 text-xs md:text-sm gap-2">
        <button
          onClick={() => setActiveTab("tracker")}
          className={`pb-3 px-4 font-semibold transition border-b-2 flex items-center gap-2 ${
            activeTab === "tracker"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>🥗</span> Daily Food Tracker
        </button>
        <button
          onClick={() => setActiveTab("targets")}
          className={`pb-3 px-4 font-semibold transition border-b-2 flex items-center gap-2 ${
            activeTab === "targets"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>⚖️</span> BMI & Target Engine
        </button>
        <button
          onClick={() => setActiveTab("dietician")}
          className={`pb-3 px-4 font-semibold transition border-b-2 flex items-center gap-2 ${
            activeTab === "dietician"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>🤖</span> AI Meal Plan
        </button>
        <button
          onClick={() => setActiveTab("grocery")}
          className={`pb-3 px-4 font-semibold transition border-b-2 flex items-center gap-2 ${
            activeTab === "grocery"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>🛒</span> Smart Grocery List
        </button>
      </div>

      {/* TAB 1: DAILY FOOD TRACKER */}
      {activeTab === "tracker" && summary && (
        <section className="mx-auto mt-6 max-w-6xl space-y-6">
          {/* Caloric & Macronutrient Progress Bar Cards */}
          <div className="grid gap-4 md:grid-cols-4">
            {/* Calories Card */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-5 shadow-sm">
              <span className="text-xs uppercase tracking-wider text-slate-400">Daily Calories</span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-extrabold text-white">{summary.total_calories}</span>
                <span className="text-xs text-slate-400">/ {summary.target_calories} kcal</span>
              </div>
              <div className="mt-3 h-2 w-full rounded-full bg-slate-800 overflow-hidden">
                <div
                  className={`h-full ${summary.calories_percentage > 105 ? "bg-rose-500" : "bg-emerald-500"} rounded-full transition-all`}
                  style={{ width: `${Math.min(100, summary.calories_percentage)}%` }}
                />
              </div>
              <p className="mt-2 text-xs text-slate-400">
                {summary.remaining_calories >= 0
                  ? `${summary.remaining_calories} kcal remaining`
                  : `${Math.abs(summary.remaining_calories)} kcal over budget`}
              </p>
            </div>

            {/* Protein Card */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-5 shadow-sm">
              <span className="text-xs uppercase tracking-wider text-blue-400 font-semibold">Protein</span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-extrabold text-white">{summary.total_protein}g</span>
                <span className="text-xs text-slate-400">/ {summary.target_protein}g</span>
              </div>
              <div className="mt-3 h-2 w-full rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full transition-all"
                  style={{ width: `${Math.min(100, summary.protein_percentage)}%` }}
                />
              </div>
              <p className="mt-2 text-xs text-slate-400">{summary.protein_percentage}% of target</p>
            </div>

            {/* Carbs Card */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-5 shadow-sm">
              <span className="text-xs uppercase tracking-wider text-amber-400 font-semibold">Carbohydrates</span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-extrabold text-white">{summary.total_carbs}g</span>
                <span className="text-xs text-slate-400">/ {summary.target_carbs}g</span>
              </div>
              <div className="mt-3 h-2 w-full rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-amber-500 rounded-full transition-all"
                  style={{ width: `${Math.min(100, summary.carbs_percentage)}%` }}
                />
              </div>
              <p className="mt-2 text-xs text-slate-400">{summary.carbs_percentage}% of target</p>
            </div>

            {/* Fat Card */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-5 shadow-sm">
              <span className="text-xs uppercase tracking-wider text-purple-400 font-semibold">Healthy Fat</span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-extrabold text-white">{summary.total_fat}g</span>
                <span className="text-xs text-slate-400">/ {summary.target_fat}g</span>
              </div>
              <div className="mt-3 h-2 w-full rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-purple-500 rounded-full transition-all"
                  style={{ width: `${Math.min(100, summary.fat_percentage)}%` }}
                />
              </div>
              <p className="mt-2 text-xs text-slate-400">{summary.fat_percentage}% of target</p>
            </div>
          </div>

          {/* Quick Actions & Header */}
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-slate-100">Today&apos;s Meal Logs ({summary.date})</h2>
            <button
              onClick={() => setLogModalOpen(true)}
              className="rounded-xl bg-emerald-600 px-4 py-2 text-xs md:text-sm font-bold text-white hover:bg-emerald-500 shadow-md shadow-emerald-600/20 transition flex items-center gap-1.5"
            >
              <span>+</span> Log Food Item
            </button>
          </div>

          {/* Meal Breakdown Sections */}
          <div className="grid gap-6 md:grid-cols-2">
            {(["breakfast", "lunch", "dinner", "snack"] as const).map((mealKey) => {
              const logs = summary.meal_breakdown[mealKey] || [];
              const mealCals = Math.round(logs.reduce((acc, l) => acc + l.calories, 0));
              const mealProt = Math.round(logs.reduce((acc, l) => acc + l.protein, 0) * 10) / 10;

              return (
                <div key={mealKey} className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
                    <div>
                      <h3 className="text-sm font-bold capitalize text-white flex items-center gap-2">
                        <span>{mealKey === "breakfast" ? "🥞" : mealKey === "lunch" ? "🍗" : mealKey === "dinner" ? "🥩" : "🍎"}</span>
                        {mealKey}
                      </h3>
                      <p className="text-[11px] text-slate-400">
                        {mealCals} kcal • {mealProt}g protein
                      </p>
                    </div>
                    <button
                      onClick={() => {
                        setSelectedMealType(mealKey);
                        setLogModalOpen(true);
                      }}
                      className="text-xs text-emerald-400 hover:text-emerald-300 font-semibold"
                    >
                      + Add
                    </button>
                  </div>

                  {logs.length === 0 ? (
                    <p className="text-xs text-slate-500 py-3 text-center italic">No items logged yet.</p>
                  ) : (
                    <ul className="divide-y divide-slate-800/60 text-xs">
                      {logs.map((item) => (
                        <li key={item.id} className="py-2.5 flex items-center justify-between">
                          <div>
                            <span className="font-semibold text-slate-200">{item.food_name}</span>
                            <p className="text-[11px] text-slate-400">
                              {item.quantity}{item.unit} • P: {item.protein}g • C: {item.carbs}g • F: {item.fat}g
                            </p>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className="font-bold text-slate-200">{item.calories} kcal</span>
                            <button
                              onClick={() => handleDeleteFoodLog(item.id)}
                              className="text-slate-500 hover:text-rose-400 transition"
                              title="Delete entry"
                            >
                              ✕
                            </button>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* TAB 2: BMI & TARGET ENGINE */}
      {activeTab === "targets" && (
        <section className="mx-auto mt-6 max-w-6xl space-y-6">
          <div className="rounded-2xl border border-slate-800 bg-gradient-to-r from-emerald-950/40 via-slate-900 to-teal-950/40 p-6 flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="space-y-1">
              <span className="rounded-full bg-emerald-900/60 border border-emerald-600 px-2.5 py-0.5 text-xs font-semibold text-emerald-300">
                Deterministic Calculation Engine
              </span>
              <h2 className="text-xl font-bold text-white mt-1">Metabolic Baseline & Daily Nutritional Targets</h2>
              <p className="text-xs md:text-sm text-slate-300 max-w-xl">
                Computed via the clinical Mifflin-St Jeor equation and standard WHO body mass thresholds, strictly customized to your training goal and activity level.
              </p>
            </div>
          </div>

          {bmiData && (
            <div className="grid gap-6 md:grid-cols-3">
              {/* BMI Card */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-6 space-y-3">
                <span className="text-xs uppercase tracking-wider text-slate-400 font-semibold">Body Mass Index (BMI)</span>
                <div className="flex items-baseline gap-3">
                  <span className="text-4xl font-extrabold text-white">{bmiData.bmi}</span>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${
                    bmiData.category === "Normal weight"
                      ? "bg-emerald-950 text-emerald-300 border border-emerald-700"
                      : "bg-amber-950 text-amber-300 border border-amber-700"
                  }`}>
                    {bmiData.category}
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  Healthy weight range for your height ({bmiData.height_cm} cm):{" "}
                  <span className="text-slate-200 font-semibold">{bmiData.healthy_weight_min_kg} kg – {bmiData.healthy_weight_max_kg} kg</span>
                </p>
              </div>

              {/* BMR & TDEE Card */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-6 space-y-3">
                <span className="text-xs uppercase tracking-wider text-slate-400 font-semibold">Energy Expenditure</span>
                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-400">Basal Metabolic Rate (BMR):</span>
                    <span className="font-bold text-white">{bmiData.bmr} kcal</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-400">Total Daily Expenditure (TDEE):</span>
                    <span className="font-bold text-emerald-400">{bmiData.tdee} kcal</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-400">Recommended Water Intake:</span>
                    <span className="font-bold text-cyan-400">{bmiData.water_liters} L/day</span>
                  </div>
                </div>
                <p className="text-[11px] text-slate-400">BMR represents minimum energy needed at full rest.</p>
              </div>

              {/* Caloric Prescription Card */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-6 space-y-3">
                <span className="text-xs uppercase tracking-wider text-slate-400 font-semibold">Prescribed Daily Target</span>
                <div className="text-3xl font-extrabold text-emerald-400">
                  {bmiData.recommended_calories} <span className="text-sm font-normal text-slate-400">kcal/day</span>
                </div>
                <div className="text-xs space-y-1 text-slate-300">
                  <p>• Protein: <span className="font-bold text-white">{bmiData.recommended_protein_g}g</span> (muscle synthesis)</p>
                  <p>• Carbs: <span className="font-bold text-white">{bmiData.recommended_carbs_g}g</span> (glycogen & energy)</p>
                  <p>• Fat: <span className="font-bold text-white">{bmiData.recommended_fat_g}g</span> (hormonal health)</p>
                </div>
              </div>
            </div>
          )}
        </section>
      )}

      {/* TAB 3: AI DIETICIAN & MEAL PLAN */}
      {activeTab === "dietician" && (
        <section className="mx-auto mt-6 max-w-6xl space-y-6">
          {/* Action Header Card */}
          <div className="rounded-2xl border border-emerald-900/50 bg-gradient-to-r from-emerald-950/40 via-slate-900 to-cyan-950/40 p-6 flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="space-y-1">
              <span className="rounded-full bg-emerald-900/60 border border-emerald-600 px-2.5 py-0.5 text-xs font-semibold text-emerald-300">
                LLM + Deterministic Constraint Engine
              </span>
              <h2 className="text-xl font-bold text-white mt-1">Personalized Daily Meal Plan</h2>
              <p className="text-xs md:text-sm text-slate-300 max-w-xl">
                Generates realistic whole-food meals mathematically balanced to your target calories and macronutrients, adhering strictly to your dietary preferences.
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-3 w-full md:w-auto">
              <button
                onClick={handleGenerateDietPlan}
                disabled={generatingPlan}
                className="rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 px-6 py-3 text-sm font-bold text-white hover:from-emerald-500 hover:to-teal-500 shadow-lg shadow-emerald-600/30 transition disabled:opacity-50"
              >
                {generatingPlan ? "Generating Plan..." : "⚡ Generate Meal Plan"}
              </button>
            </div>
          </div>

          {/* Preferences Selector Box */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-5 grid gap-4 md:grid-cols-3">
            <div>
              <label className="text-xs text-slate-400 font-semibold">Dietary Preference</label>
              <select
                value={planPref}
                onChange={(e) => setPlanPref(e.target.value)}
                className="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-white"
              >
                <option value="standard">Standard (Omnivore / High Balance)</option>
                <option value="vegetarian">Vegetarian (Lacto-Ovo)</option>
                <option value="vegan">Vegan (100% Plant-Based)</option>
                <option value="keto">Ketogenic (High Fat / Low Carb)</option>
                <option value="high_protein">High Protein (Hypertrophy / Cut)</option>
              </select>
            </div>

            <div>
              <label className="text-xs text-slate-400 font-semibold">Meals Per Day</label>
              <select
                value={planMealsCount}
                onChange={(e) => setPlanMealsCount(Number(e.target.value))}
                className="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-white"
              >
                <option value={3}>3 Meals (Breakfast, Lunch, Dinner)</option>
                <option value={4}>4 Meals (Breakfast, Lunch, Dinner, Snack)</option>
              </select>
            </div>

            <div>
              <label className="text-xs text-slate-400 font-semibold">Allergies / Exclusions</label>
              <input
                type="text"
                value={planAllergies}
                onChange={(e) => setPlanAllergies(e.target.value)}
                placeholder="e.g. peanuts, lactose, shellfish"
                className="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-white placeholder-slate-500"
              />
            </div>
          </div>

          {/* Generated Diet Plan Display */}
          {dietPlan ? (
            <div className="space-y-6">
              {/* Plan Summary Banner */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-5 flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h3 className="text-base font-bold text-white">
                    Diet Plan: {dietPlan.dietary_preference.toUpperCase()} ({dietPlan.goal.replace("_", " ").toUpperCase()})
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">{dietPlan.notes}</p>
                </div>
                <div className="flex gap-4 text-xs">
                  <span className="rounded bg-slate-800 px-3 py-1 text-slate-200 font-bold">
                    🔥 {dietPlan.total_plan_calories} kcal
                  </span>
                  <span className="rounded bg-slate-800 px-3 py-1 text-blue-300 font-bold">
                    🥩 {dietPlan.total_plan_protein}g Protein
                  </span>
                  <span className="rounded bg-slate-800 px-3 py-1 text-amber-300 font-bold">
                    🌾 {dietPlan.total_plan_carbs}g Carbs
                  </span>
                  <span className="rounded bg-slate-800 px-3 py-1 text-purple-300 font-bold">
                    🥑 {dietPlan.total_plan_fat}g Fat
                  </span>
                </div>
              </div>

              {/* Meal Cards */}
              <div className="grid gap-6 md:grid-cols-2">
                {dietPlan.meals.map((m, idx) => (
                  <div key={idx} className="rounded-xl border border-slate-800 bg-slate-900/80 p-5 space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
                      <div>
                        <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-400">
                          {m.meal_type}
                        </span>
                        <h4 className="text-sm font-bold text-white mt-0.5">{m.meal_name}</h4>
                      </div>
                      <span className="rounded bg-emerald-950 border border-emerald-800 px-2.5 py-1 text-xs font-bold text-emerald-300">
                        {m.total_calories} kcal
                      </span>
                    </div>

                    <ul className="space-y-2 text-xs">
                      {m.items.map((it, itIdx) => (
                        <li key={itIdx} className="flex justify-between items-center text-slate-300">
                          <span>{it.name} <span className="text-slate-500">({it.quantity})</span></span>
                          <span className="text-slate-400 font-mono text-[11px]">{it.calories} kcal</span>
                        </li>
                      ))}
                    </ul>

                    {m.instructions && (
                      <div className="pt-2 border-t border-slate-800/80 text-[11px] text-slate-400 italic">
                        💡 {m.instructions}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Clinical / Wellness Disclaimer */}
              <div className="rounded-xl border border-slate-800/80 bg-slate-900/50 p-4 text-xs text-slate-400">
                ⚖️ <span className="font-semibold text-slate-300">Wellness Disclaimer:</span> {dietPlan.disclaimer}
              </div>
            </div>
          ) : (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-10 text-center space-y-3">
              <span className="text-4xl">🥗</span>
              <h3 className="text-base font-bold text-white">No Meal Plan Generated Yet</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Click the &quot;Generate Meal Plan&quot; button above to create a personalized, scientifically balanced daily menu tailored to your body weight and training targets.
              </p>
            </div>
          )}
        </section>
      )}

      {/* TAB 4: SMART GROCERY LIST */}
      {activeTab === "grocery" && (
        <section className="mx-auto mt-6 max-w-6xl space-y-6">
          <div className="rounded-2xl border border-slate-800 bg-gradient-to-r from-teal-950/40 via-slate-900 to-emerald-950/40 p-6 flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="space-y-1">
              <span className="rounded-full bg-teal-900/60 border border-teal-600 px-2.5 py-0.5 text-xs font-semibold text-teal-300">
                Automatic Ingredient Aggregation
              </span>
              <h2 className="text-xl font-bold text-white mt-1">Smart Categorized Grocery List</h2>
              <p className="text-xs md:text-sm text-slate-300 max-w-xl">
                Automatically extracted from your active meal plan, grouped into supermarket aisles (Protein, Produce, Grains, Healthy Fats) with interactive check-off capabilities.
              </p>
            </div>
          </div>

          {dietPlan?.grocery_list && dietPlan.grocery_list.length > 0 ? (
            <div className="grid gap-6 md:grid-cols-3">
              {dietPlan.grocery_list.map((catGroup) => (
                <div key={catGroup.category} className="rounded-xl border border-slate-800 bg-slate-900/80 p-5 space-y-3">
                  <h3 className="text-sm font-bold text-emerald-400 border-b border-slate-800 pb-2 flex items-center justify-between">
                    <span>{catGroup.category}</span>
                    <span className="text-xs text-slate-500 font-normal">{catGroup.items.length} items</span>
                  </h3>
                  <ul className="space-y-2 text-xs">
                    {catGroup.items.map((item, idx) => {
                      const itemKey = `${catGroup.category}_${idx}`;
                      const isChecked = !!checkedItems[itemKey];
                      return (
                        <li
                          key={idx}
                          onClick={() => toggleGroceryCheck(itemKey)}
                          className={`flex items-center gap-2.5 cursor-pointer p-1.5 rounded transition ${
                            isChecked ? "text-slate-500 line-through bg-slate-800/30" : "text-slate-200 hover:bg-slate-800/50"
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => {}}
                            className="rounded border-slate-700 text-emerald-600 focus:ring-0 cursor-pointer"
                          />
                          <span>{item}</span>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-10 text-center space-y-3">
              <span className="text-4xl">🛒</span>
              <h3 className="text-base font-bold text-white">No Grocery List Available</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Generate a meal plan in the AI Meal Plan tab to automatically populate your categorized shopping list.
              </p>
              <button
                onClick={() => setActiveTab("dietician")}
                className="mt-2 rounded-xl bg-emerald-600 px-5 py-2 text-xs font-bold text-white hover:bg-emerald-500 transition"
              >
                Go to AI Meal Plan
              </button>
            </div>
          )}
        </section>
      )}

      {/* LOG FOOD MODAL DIALOG */}
      {logModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white">Log Food to Daily Tracker</h3>
              <button
                onClick={() => setLogModalOpen(false)}
                className="text-slate-400 hover:text-white text-lg font-bold"
              >
                ✕
              </button>
            </div>

            {/* Quick search catalogue */}
            <div>
              <label className="text-xs text-slate-400 font-semibold">Search Verified Foods</label>
              <input
                type="text"
                value={foodSearch}
                onChange={(e) => setFoodSearch(e.target.value)}
                placeholder="Search eggs, chicken, rice, oats, paneer..."
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-white placeholder-slate-500"
              />
              <div className="mt-2 max-h-28 overflow-y-auto flex flex-wrap gap-1.5">
                {filteredCatalogue.map((f) => (
                  <button
                    key={f.id}
                    type="button"
                    onClick={() => handleSelectCatalogueItem(f)}
                    className="rounded-md border border-slate-700 bg-slate-800/80 px-2 py-1 text-[11px] text-slate-300 hover:bg-emerald-950 hover:border-emerald-700 hover:text-emerald-300 transition"
                  >
                    + {f.name}
                  </button>
                ))}
              </div>
            </div>

            <form onSubmit={handleFoodLogSubmit} className="space-y-3 pt-2">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400 font-semibold">Meal Type</label>
                  <select
                    value={selectedMealType}
                    onChange={(e) => setSelectedMealType(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-white"
                  >
                    <option value="breakfast">Breakfast</option>
                    <option value="lunch">Lunch</option>
                    <option value="dinner">Dinner</option>
                    <option value="snack">Snack</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-slate-400 font-semibold">Food Name</label>
                  <input
                    type="text"
                    required
                    value={foodName}
                    onChange={(e) => setFoodName(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400 font-semibold">Quantity</label>
                  <input
                    type="number"
                    min="1"
                    value={quantity}
                    onChange={(e) => handleQuantityChange(Number(e.target.value))}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 font-semibold">Calories (kcal)</label>
                  <input
                    type="number"
                    min="0"
                    value={calories}
                    onChange={(e) => setCalories(Number(e.target.value))}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs text-blue-400 font-semibold">Protein (g)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    value={protein}
                    onChange={(e) => setProtein(Number(e.target.value))}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="text-xs text-amber-400 font-semibold">Carbs (g)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    value={carbs}
                    onChange={(e) => setCarbs(Number(e.target.value))}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="text-xs text-purple-400 font-semibold">Fat (g)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    value={fat}
                    onChange={(e) => setFat(Number(e.target.value))}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-white"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setLogModalOpen(false)}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-emerald-600 px-5 py-2 text-xs font-bold text-white hover:bg-emerald-500 shadow-md shadow-emerald-600/30"
                >
                  Save Entry
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}

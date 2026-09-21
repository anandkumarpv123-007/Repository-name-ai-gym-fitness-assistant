"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE_URL } from "@/api/config";

export default function ProfilePage() {
  const router = useRouter();

  // User account info
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");

  // Fitness profile fields
  const [dateOfBirth, setDateOfBirth] = useState("");
  const [gender, setGender] = useState("");
  const [heightCm, setHeightCm] = useState("");
  const [weightKg, setWeightKg] = useState("");
  const [fitnessGoal, setFitnessGoal] = useState("");
  const [activityLevel, setActivityLevel] = useState("");
  const [dietaryPreference, setDietaryPreference] = useState("");

  // UI status
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    async function loadProfile() {
      const token = localStorage.getItem("access_token");

      if (!token) {
        router.push("/login");
        return;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/users/me`, {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.status === 401) {
          localStorage.removeItem("access_token");
          router.push("/login");
          return;
        }

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || "Failed to load profile");
        }

        setName(data.name || "");
        setEmail(data.email || "");
        setDateOfBirth(data.date_of_birth ? data.date_of_birth.split("T")[0] : "");
        setGender(data.gender || "");
        setHeightCm(
          data.height_cm !== null && data.height_cm !== undefined
            ? String(data.height_cm)
            : ""
        );
        setWeightKg(
          data.weight_kg !== null && data.weight_kg !== undefined
            ? String(data.weight_kg)
            : ""
        );
        setFitnessGoal(data.fitness_goal || "");
        setActivityLevel(data.activity_level || "");
        setDietaryPreference(data.dietary_preference || "");
      } catch (err) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Failed to load profile data");
        }
      } finally {
        setLoading(false);
      }
    }

    loadProfile();
  }, [router]);

  async function handleSave(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setError("");
    setSuccess("");
    setSaving(true);

    const token = localStorage.getItem("access_token");

    if (!token) {
      router.push("/login");
      return;
    }

    try {
      const payload = {
        date_of_birth: dateOfBirth || null,
        gender: gender || null,
        height_cm: heightCm ? parseFloat(heightCm) : null,
        weight_kg: weightKg ? parseFloat(weightKg) : null,
        fitness_goal: fitnessGoal || null,
        activity_level: activityLevel || null,
        dietary_preference: dietaryPreference || null,
      };

      const response = await fetch(`${API_BASE_URL}/users/me`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (response.status === 401) {
        localStorage.removeItem("access_token");
        router.push("/login");
        return;
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to update profile");
      }

      setSuccess("Profile updated successfully!");
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to save profile");
      }
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-white">
        <p className="text-slate-400">Loading your profile...</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 p-6 md:p-10 text-white">
      <div className="mx-auto max-w-3xl">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              Fitness Profile & Onboarding
            </h1>
            <p className="mt-2 text-slate-400 text-sm">
              Update your physical measurements and personal goals for tailored AI recommendations.
            </p>
          </div>

          <button
            type="button"
            onClick={() => router.push("/dashboard")}
            className="self-start sm:self-auto rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm font-medium hover:bg-slate-800 transition"
          >
            ← Back to Dashboard
          </button>
        </div>

        {/* Account Info Bar */}
        <div className="mt-6 rounded-xl border border-slate-800 bg-slate-900/60 p-5 flex flex-wrap gap-6 text-sm text-slate-300">
          <div>
            <span className="text-slate-500">Account Name:</span>{" "}
            <span className="font-semibold text-white">{name || "User"}</span>
          </div>
          <div>
            <span className="text-slate-500">Email:</span>{" "}
            <span className="font-semibold text-white">{email}</span>
          </div>
        </div>

        {/* Notifications */}
        {error && (
          <div className="mt-6 rounded-lg bg-red-900/30 border border-red-800 p-4 text-sm text-red-400">
            {error}
          </div>
        )}

        {success && (
          <div className="mt-6 rounded-lg bg-emerald-900/30 border border-emerald-800 p-4 text-sm text-emerald-400 flex items-center justify-between">
            <span>✓ {success}</span>
            <button
              type="button"
              onClick={() => router.push("/dashboard")}
              className="underline text-emerald-300 hover:text-emerald-200 text-xs font-medium ml-4"
            >
              View Dashboard →
            </button>
          </div>
        )}

        {/* Profile Form */}
        <form onSubmit={handleSave} className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-8 space-y-6">
          {/* Row 1: Date of Birth & Gender */}
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300">
                Date of Birth
              </label>
              <input
                type="date"
                value={dateOfBirth}
                onChange={(e) => setDateOfBirth(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-3 text-white outline-none focus:border-blue-500 transition"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300">
                Gender
              </label>
              <select
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-3 text-white outline-none focus:border-blue-500 transition"
              >
                <option value="">Select Gender</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
                <option value="prefer_not_to_say">Prefer not to say</option>
              </select>
            </div>
          </div>

          {/* Row 2: Height & Weight */}
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300">
                Height (cm)
              </label>
              <input
                type="number"
                step="0.1"
                min="50"
                max="300"
                placeholder="e.g. 175.0"
                value={heightCm}
                onChange={(e) => setHeightCm(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-3 text-white outline-none focus:border-blue-500 transition"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300">
                Weight (kg)
              </label>
              <input
                type="number"
                step="0.1"
                min="20"
                max="500"
                placeholder="e.g. 70.0"
                value={weightKg}
                onChange={(e) => setWeightKg(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-3 text-white outline-none focus:border-blue-500 transition"
              />
            </div>
          </div>

          {/* Row 3: Fitness Goal */}
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300">
              Primary Fitness Goal
            </label>
            <select
              value={fitnessGoal}
              onChange={(e) => setFitnessGoal(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-3 text-white outline-none focus:border-blue-500 transition"
            >
              <option value="">Select a Goal</option>
              <option value="muscle_gain">Muscle Gain (Hypertrophy)</option>
              <option value="weight_loss">Weight Loss / Fat Burn</option>
              <option value="endurance">Endurance & Stamina</option>
              <option value="maintenance">Maintenance & Longevity</option>
              <option value="flexibility">Flexibility & Mobility</option>
              <option value="general_fitness">General Health & Fitness</option>
            </select>
          </div>

          {/* Row 4: Activity Level & Dietary Preference */}
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300">
                Activity Level
              </label>
              <select
                value={activityLevel}
                onChange={(e) => setActivityLevel(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-3 text-white outline-none focus:border-blue-500 transition"
              >
                <option value="">Select Activity Level</option>
                <option value="sedentary">Sedentary (Little or no exercise)</option>
                <option value="lightly_active">Lightly Active (1-3 days/week)</option>
                <option value="moderately_active">Moderately Active (3-5 days/week)</option>
                <option value="very_active">Very Active (6-7 days/week)</option>
                <option value="extra_active">Extra Active (Intense training / physical job)</option>
              </select>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-slate-300">
                Dietary Preference
              </label>
              <select
                value={dietaryPreference}
                onChange={(e) => setDietaryPreference(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-3 text-white outline-none focus:border-blue-500 transition"
              >
                <option value="">Select Dietary Preference</option>
                <option value="no_preference">No Specific Preference</option>
                <option value="vegetarian">Vegetarian</option>
                <option value="vegan">Vegan</option>
                <option value="keto">Ketogenic (Keto)</option>
                <option value="paleo">Paleo</option>
                <option value="pescatarian">Pescatarian</option>
                <option value="gluten_free">Gluten-Free</option>
              </select>
            </div>
          </div>

          {/* Actions */}
          <div className="pt-4 flex flex-col sm:flex-row items-center gap-4">
            <button
              type="submit"
              disabled={saving}
              className="w-full sm:w-auto rounded-lg bg-blue-600 px-8 py-3.5 font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 transition"
            >
              {saving ? "Saving Changes..." : "Save Profile"}
            </button>

            <button
              type="button"
              onClick={() => router.push("/dashboard")}
              className="w-full sm:w-auto rounded-lg border border-slate-700 px-6 py-3.5 font-medium text-slate-300 hover:bg-slate-800 transition"
            >
              Return to Dashboard
            </button>
          </div>
        </form>
      </div>
    </main>
  );
}


"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE_URL } from "@/api/config";

type Profile = {
  name: string;
  email: string;
  height_cm: number | null;
  weight_kg: number | null;
  fitness_goal: string | null;
  activity_level: string | null;
  dietary_preference: string | null;
};

export default function Dashboard() {
  const router = useRouter();

  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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

        setProfile(data);
      } catch (error) {
        if (error instanceof Error) {
          setError(error.message);
        } else {
          setError("Something went wrong");
        }
      } finally {
        setLoading(false);
      }
    }

    loadProfile();
  }, [router]);

  function handleLogout() {
    localStorage.removeItem("access_token");
    router.push("/login");
  }

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-white">
        <p className="text-slate-400">Loading your profile...</p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-white">
        <div className="rounded-xl border border-red-900 bg-slate-900 p-8">
          <h1 className="text-xl font-semibold text-red-400">
            Error
          </h1>

          <p className="mt-3 text-slate-400">
            {error}
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 p-8 text-white">

      <header className="mx-auto flex max-w-6xl items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">
            AI Gym Dashboard
          </h1>

          <p className="mt-2 text-slate-400">
            Welcome back, {profile?.name} 👋
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/workout")}
            className="rounded-lg bg-gradient-to-r from-blue-600 to-teal-600 px-5 py-2 text-sm font-semibold text-white hover:from-blue-500 hover:to-teal-500 shadow-md shadow-blue-500/20 transition"
          >
            + Start Workout
          </button>

          <button
            onClick={() => router.push("/planner")}
            className="rounded-lg border border-purple-600/50 bg-purple-950/40 px-4 py-2 text-sm font-medium text-purple-300 hover:bg-purple-900/60 transition"
          >
            Gym & Planner
          </button>

          <button
            onClick={() => router.push("/iot")}
            className="rounded-lg border border-cyan-600/50 bg-cyan-950/40 px-4 py-2 text-sm font-medium text-cyan-300 hover:bg-cyan-900/60 transition"
          >
            Smart Gym IoT
          </button>

          <button
            onClick={() => router.push("/habit")}
            className="rounded-lg border border-indigo-600/50 bg-indigo-950/40 px-4 py-2 text-sm font-medium text-indigo-300 hover:bg-indigo-900/60 transition"
          >
            Habit Tracker
          </button>

          <button
            onClick={() => router.push("/reports")}
            className="rounded-lg border border-teal-600/50 bg-teal-950/40 px-4 py-2 text-sm font-medium text-teal-300 hover:bg-teal-900/60 transition"
          >
            Weekly Intelligence
          </button>

          <button
            onClick={() => router.push("/nutrition")}
            className="rounded-lg border border-emerald-600/50 bg-emerald-950/40 px-4 py-2 text-sm font-medium text-emerald-300 hover:bg-emerald-900/60 transition"
          >
            Nutrition & Diet
          </button>

          <button
            onClick={() => router.push("/history")}
            className="rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-medium hover:bg-slate-800 transition"
          >
            History
          </button>

          <button
            onClick={() => router.push("/profile")}
            className="rounded-lg border border-blue-600 bg-blue-600/20 px-4 py-2 text-sm font-medium text-blue-400 hover:bg-blue-600 hover:text-white transition"
          >
            Edit Profile
          </button>

          <button
            onClick={handleLogout}
            className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium hover:bg-slate-800 transition"
          >
            Logout
          </button>
        </div>
      </header>

      {/* Phase 2 Quick Launch Banner */}
      <section className="mx-auto mt-8 max-w-6xl rounded-2xl border border-blue-900/50 bg-gradient-to-r from-blue-950/40 via-slate-900 to-teal-950/40 p-6 flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="space-y-1">
          <span className="rounded-full bg-blue-900/60 border border-blue-600 px-2.5 py-0.5 text-xs font-semibold text-blue-300">
            Phase 2 Vision Engine Ready
          </span>
          <h2 className="text-xl font-bold text-white mt-1">Real-Time AI Fitness Coach</h2>
          <p className="text-xs md:text-sm text-slate-300 max-w-xl">
            Track your repetitions, measure precise knee flexion angles, monitor biomechanical tempo, and receive instant posture feedback with MediaPipe computer vision.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => router.push("/workout")}
            className="rounded-xl bg-blue-600 px-6 py-3 text-sm font-bold text-white hover:bg-blue-500 shadow-lg shadow-blue-600/30 transition"
          >
            Launch AI Trainer
          </button>
        </div>
      </section>

      <section className="mx-auto mt-8 grid max-w-6xl gap-6 md:grid-cols-3">

        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="text-lg font-semibold">
            Height
          </h2>

          <p className="mt-3 text-2xl font-bold">
            {profile?.height_cm ?? "Not set"}{" "}
            {profile?.height_cm ? "cm" : ""}
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="text-lg font-semibold">
            Weight
          </h2>

          <p className="mt-3 text-2xl font-bold">
            {profile?.weight_kg ?? "Not set"}{" "}
            {profile?.weight_kg ? "kg" : ""}
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="text-lg font-semibold">
            Fitness Goal
          </h2>

          <p className="mt-3 text-2xl font-bold">
            {profile?.fitness_goal ?? "Not set"}
          </p>
        </div>

      </section>

      <section className="mx-auto mt-8 max-w-6xl rounded-xl border border-slate-800 bg-slate-900 p-6">

        <h2 className="text-xl font-semibold">
          Your Profile
        </h2>

        <div className="mt-5 grid gap-4 md:grid-cols-2">

          <p className="text-slate-300">
            <span className="text-slate-500">Email:</span>{" "}
            {profile?.email}
          </p>

          <p className="text-slate-300">
            <span className="text-slate-500">Activity:</span>{" "}
            {profile?.activity_level ?? "Not set"}
          </p>

          <p className="text-slate-300">
            <span className="text-slate-500">Diet:</span>{" "}
            {profile?.dietary_preference ?? "Not set"}
          </p>

        </div>

      </section>

    </main>
  );
}

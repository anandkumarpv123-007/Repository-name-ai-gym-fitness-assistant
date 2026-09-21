import Link from "next/link";
export default function Home() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <header className="flex items-center justify-between px-8 py-6">
        <h1 className="text-2xl font-bold">
          AI Gym
        </h1>

        <Link
          href="/login"
          className="rounded-lg bg-blue-600 px-5 py-2 font-medium hover:bg-blue-700"
        >
          Login
        </Link>
      </header>

      {/* Hero Section */}
      <section className="mx-auto flex max-w-6xl flex-col items-center px-8 py-24 text-center">
        <p className="mb-4 text-sm font-semibold uppercase tracking-widest text-blue-400">
          AI-Powered Fitness
        </p>

        <h2 className="max-w-4xl text-5xl font-bold leading-tight">
          Your Personal
          <span className="text-blue-400"> AI Fitness Assistant</span>
        </h2>

        <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
          Train smarter with AI-powered workout analysis, personalized
          nutrition, fitness tracking, and intelligent guidance.
        </p>

        <div className="mt-10 flex gap-4">
          <button className="rounded-lg bg-blue-600 px-6 py-3 font-semibold hover:bg-blue-700">
            Get Started
          </button>

          <button className="rounded-lg border border-slate-600 px-6 py-3 font-semibold hover:bg-slate-800">
            Explore Features
          </button>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto grid max-w-6xl gap-6 px-8 pb-20 md:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h3 className="text-xl font-semibold">
            AI Gym Trainer
          </h3>

          <p className="mt-3 text-slate-400">
            Analyze exercise posture, count repetitions, and receive
            real-time form feedback.
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h3 className="text-xl font-semibold">
            AI Dietician
          </h3>

          <p className="mt-3 text-slate-400">
            Get personalized nutrition guidance based on your goals,
            profile, and dietary preferences.
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h3 className="text-xl font-semibold">
            Fitness Analytics
          </h3>

          <p className="mt-3 text-slate-400">
            Track workouts, performance, habits, and long-term fitness
            progress.
          </p>
        </div>
      </section>
    </main>
  );
}
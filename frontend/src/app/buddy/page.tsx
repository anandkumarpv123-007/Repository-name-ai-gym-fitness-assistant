"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { API_BASE_URL } from "@/api/config";

interface BuddyMessageItem {
  id: number;
  sender: string;
  content: string;
  provider?: string | null;
  created_at: string;
}

interface ContextSummary {
  profile?: {
    fitness_goal?: string;
    activity_level?: string;
    height_cm?: number;
    weight_kg?: number;
  };
  workout_performance?: {
    total_workouts?: number;
    avg_performance_score?: number;
    top_exercise?: string;
    next_week_focus?: string;
  };
  nutrition?: {
    target_calories?: number;
    consumed_calories_today?: number;
    remaining_calories_today?: number;
    target_protein?: number;
    consumed_protein_today?: number;
  };
}

export default function VirtualGymBuddyPage() {
  const router = useRouter();

  const [messages, setMessages] = useState<BuddyMessageItem[]>([]);
  const [inputText, setInputText] = useState("");
  const [loading, setLoading] = useState(false);
  const [initLoading, setInitLoading] = useState(true);
  const [error, setError] = useState("");
  const [contextSummary, setContextSummary] = useState<ContextSummary | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    async function loadHistory() {
      const token = localStorage.getItem("access_token");
      if (!token) {
        router.push("/login");
        return;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/buddy/history`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (response.status === 401) {
          localStorage.removeItem("access_token");
          router.push("/login");
          return;
        }

        if (response.ok) {
          const data = await response.json();
          setMessages(data.messages || []);
        }
      } catch (err) {
        console.error("Failed to load chat history", err);
      } finally {
        setInitLoading(false);
      }
    }

    loadHistory();
  }, [router]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSendMessage = async (textToSend?: string) => {
    const msg = (textToSend || inputText).trim();
    if (!msg || loading) return;

    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
      return;
    }

    setError("");
    setInputText("");
    setLoading(true);

    // Optimistic local add
    const tempUserMsg: BuddyMessageItem = {
      id: Date.now(),
      sender: "user",
      content: msg,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const res = await fetch(`${API_BASE_URL}/buddy/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message: msg, include_history: true }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Failed to communicate with Virtual Gym Buddy");
      }

      const tempBotMsg: BuddyMessageItem = {
        id: Date.now() + 1,
        sender: "assistant",
        content: data.message,
        provider: data.provider,
        created_at: data.timestamp || new Date().toISOString(),
      };

      setMessages((prev) => [...prev, tempBotMsg]);

      if (data.context_summary) {
        setContextSummary(data.context_summary);
      }
    } catch (err: any) {
      setError(err.message || "Network error while connecting to Virtual Gym Buddy");
    } finally {
      setLoading(false);
    }
  };

  const handleClearHistory = async () => {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    if (!confirm("Are you sure you want to clear all Virtual Gym Buddy chat history?")) {
      return;
    }

    try {
      const res = await fetch(`${API_BASE_URL}/buddy/history`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        setMessages([]);
      }
    } catch (err) {
      console.error("Failed to clear chat history", err);
    }
  };

  const quickPrompts = [
    { emoji: "📊", label: "How did I perform this week?", text: "How did I perform this week?" },
    { emoji: "🎯", label: "What should I focus on next?", text: "What should I focus on in my next workout?" },
    { emoji: "🥗", label: "How is my nutrition today?", text: "How am I doing with my nutrition today?" },
    { emoji: "🔥", label: "Give me workout motivation!", text: "Give me some motivation for today's workout." },
  ];

  const getProviderBadge = (provider?: string | null) => {
    if (!provider) return null;
    if (provider.includes("gemini")) {
      return <span className="rounded bg-indigo-900/60 px-2 py-0.5 text-xs font-semibold text-indigo-300 border border-indigo-700/50">⚡ Gemini AI</span>;
    }
    if (provider.includes("openai")) {
      return <span className="rounded bg-purple-900/60 px-2 py-0.5 text-xs font-semibold text-purple-300 border border-purple-700/50">✨ OpenAI</span>;
    }
    if (provider.includes("safety")) {
      return <span className="rounded bg-amber-900/60 px-2 py-0.5 text-xs font-semibold text-amber-300 border border-amber-700/50">🛡️ Medical Safety Boundary</span>;
    }
    return <span className="rounded bg-teal-900/60 px-2 py-0.5 text-xs font-semibold text-teal-300 border border-teal-700/50">🤖 Deterministic Engine</span>;
  };

  return (
    <div className="flex flex-col min-h-screen bg-slate-950 text-white font-sans">
      {/* Header Bar */}
      <header className="sticky top-0 z-30 border-b border-slate-800 bg-slate-900/90 backdrop-blur-md px-6 py-4">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 to-teal-500 font-bold text-white shadow-lg shadow-indigo-500/20">
              🤖
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-wide">Virtual Gym Buddy</h1>
              <p className="text-xs text-slate-400">Authenticated AI Fitness & Nutrition Assistant</p>
            </div>
          </div>

          <nav className="flex items-center gap-3">
            <Link href="/dashboard" className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-800 transition">Dashboard</Link>
            <Link href="/workout" className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-500 transition">+ Workout</Link>
            <Link href="/reports" className="rounded-lg border border-teal-700/60 bg-teal-950/40 px-3 py-1.5 text-xs font-medium text-teal-300 hover:bg-teal-900/60 transition">Intelligence</Link>
            <Link href="/nutrition" className="rounded-lg border border-emerald-700/60 bg-emerald-950/40 px-3 py-1.5 text-xs font-medium text-emerald-300 hover:bg-emerald-900/60 transition">Nutrition</Link>
            <span className="rounded-lg border border-indigo-500 bg-indigo-600/30 px-3 py-1.5 text-xs font-medium text-indigo-200">Buddy Chat</span>
            <button onClick={handleClearHistory} className="rounded-lg border border-red-900/50 bg-red-950/30 px-3 py-1.5 text-xs font-medium text-red-300 hover:bg-red-900/50 transition">Clear Chat</button>
          </nav>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="mx-auto flex w-full max-w-7xl flex-1 gap-6 p-6">
        {/* Chat Stream Window */}
        <div className="flex flex-1 flex-col rounded-2xl border border-slate-800 bg-slate-900/50 shadow-2xl backdrop-blur-sm overflow-hidden">
          {/* Quick Action Chips Bar */}
          <div className="border-b border-slate-800/80 bg-slate-900/80 p-3 flex flex-wrap gap-2 items-center">
            <span className="text-xs font-semibold text-slate-400 mr-1">Quick Prompts:</span>
            {quickPrompts.map((qp, idx) => (
              <button
                key={idx}
                disabled={loading}
                onClick={() => handleSendMessage(qp.text)}
                className="flex items-center gap-1.5 rounded-full border border-indigo-900/50 bg-indigo-950/40 px-3 py-1 text-xs text-indigo-300 hover:bg-indigo-900/60 hover:border-indigo-600 transition disabled:opacity-50"
              >
                <span>{qp.emoji}</span>
                <span>{qp.label}</span>
              </button>
            ))}
          </div>

          {/* Messages Stream */}
          <div className="flex-1 overflow-y-auto p-6 space-y-5 min-h-[420px]">
            {initLoading ? (
              <div className="flex h-full items-center justify-center text-slate-400 text-sm">
                Loading Virtual Gym Buddy conversation history...
              </div>
            ) : messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center text-slate-400">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-950 border border-indigo-800 text-3xl mb-4">
                  💬
                </div>
                <h3 className="text-lg font-semibold text-slate-200">No Messages Yet</h3>
                <p className="mt-1 text-xs text-slate-400 max-w-md">
                  Ask me anything about your weekly workout performance, squat form, daily nutrition, or workout motivation!
                </p>
              </div>
            ) : (
              messages.map((m) => {
                const isUser = m.sender === "user";
                return (
                  <div key={m.id} className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs text-slate-500 font-medium">{isUser ? "You" : "Virtual Gym Buddy"}</span>
                      {!isUser && getProviderBadge(m.provider)}
                    </div>

                    <div
                      className={`max-w-2xl rounded-2xl p-4 text-sm leading-relaxed whitespace-pre-wrap ${
                        isUser
                          ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-tr-none shadow-md shadow-blue-500/10"
                          : "bg-slate-800/90 text-slate-100 border border-slate-700/80 rounded-tl-none"
                      }`}
                    >
                      {m.content}
                    </div>

                    {!isUser && (
                      <span className="mt-1 text-[10px] text-slate-500">
                        Fitness Assistant • Scoped to current authenticated context
                      </span>
                    )}
                  </div>
                );
              })
            )}

            {loading && (
              <div className="flex flex-col items-start space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500 font-medium">Virtual Gym Buddy</span>
                  <span className="rounded bg-indigo-900/40 px-2 py-0.5 text-xs text-indigo-300 animate-pulse">Thinking...</span>
                </div>
                <div className="rounded-2xl rounded-tl-none bg-slate-800/80 p-4 border border-slate-700/60 text-sm text-slate-400 flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-indigo-400 animate-ping" />
                  Analyzing your profile, weekly workouts, and nutrition logs...
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Error Banner */}
          {error && (
            <div className="mx-6 mb-3 rounded-lg border border-red-900/80 bg-red-950/60 p-3 text-xs text-red-300">
              ⚠️ {error}
            </div>
          )}

          {/* Message Input Box */}
          <div className="border-t border-slate-800 bg-slate-900/90 p-4">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="flex items-center gap-3"
            >
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Ask Virtual Gym Buddy (e.g., 'How was my squat form this week?')"
                disabled={loading}
                className="flex-1 rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={loading || !inputText.trim()}
                className="rounded-xl bg-gradient-to-r from-indigo-600 to-teal-500 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-500/20 hover:from-indigo-500 hover:to-teal-400 transition disabled:opacity-50"
              >
                Send 🚀
              </button>
            </form>
            <p className="mt-2 text-[11px] text-center text-slate-500">
              Virtual Gym Buddy uses your real logged data to provide personalized coaching answers.
            </p>
          </div>
        </div>

        {/* Right Sidebar: Context Snapshot */}
        <aside className="hidden lg:flex w-80 flex-col gap-4">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur-sm">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span>🎯</span> Active User Context
            </h3>
            <p className="mt-1 text-xs text-slate-400">
              Live context supplied to Virtual Gym Buddy for personalized answers.
            </p>

            {contextSummary ? (
              <div className="mt-4 space-y-4 text-xs">
                {/* Profile Block */}
                <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                  <h4 className="font-semibold text-indigo-300 mb-1">User Profile</h4>
                  <div className="space-y-0.5 text-slate-300">
                    <p>Goal: <span className="font-medium text-white">{contextSummary.profile?.fitness_goal || "Not set"}</span></p>
                    <p>Activity: <span className="font-medium text-white">{contextSummary.profile?.activity_level || "Not set"}</span></p>
                  </div>
                </div>

                {/* Workout Block */}
                <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                  <h4 className="font-semibold text-teal-300 mb-1">7-Day Workout Performance</h4>
                  <div className="space-y-0.5 text-slate-300">
                    <p>Workouts Logged: <span className="font-medium text-white">{contextSummary.workout_performance?.total_workouts ?? 0}</span></p>
                    <p>Avg Score: <span className="font-medium text-white">{contextSummary.workout_performance?.avg_performance_score ?? "N/A"}/100</span></p>
                    <p>Next Focus: <span className="font-medium text-white">{contextSummary.workout_performance?.next_week_focus || "Consistency"}</span></p>
                  </div>
                </div>

                {/* Nutrition Block */}
                <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                  <h4 className="font-semibold text-emerald-300 mb-1">Today's Nutrition</h4>
                  <div className="space-y-0.5 text-slate-300">
                    <p>Target Cals: <span className="font-medium text-white">{contextSummary.nutrition?.target_calories ?? "N/A"} kcal</span></p>
                    <p>Consumed: <span className="font-medium text-white">{contextSummary.nutrition?.consumed_calories_today ?? 0} kcal</span></p>
                    <p>Protein Target: <span className="font-medium text-white">{contextSummary.nutrition?.target_protein ?? "N/A"}g</span></p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950 p-4 text-xs text-slate-500 text-center">
                Send a message to view the exact snapshot of data Virtual Gym Buddy retrieved.
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-amber-900/40 bg-amber-950/20 p-4 text-xs text-amber-200/90 leading-relaxed">
            <span className="font-bold text-amber-300 block mb-1">🛡️ Safety Disclaimer</span>
            Virtual Gym Buddy is designed for fitness, form coaching, and wellness guidance. It does not provide medical diagnoses or treatment for injuries.
          </div>
        </aside>
      </div>
    </div>
  );
}

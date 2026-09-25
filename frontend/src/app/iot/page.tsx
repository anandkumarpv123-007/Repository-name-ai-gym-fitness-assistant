"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE_URL } from "@/api/config";

interface IoTDevice {
  id: number;
  user_id: number;
  device_uid: string;
  device_name: string;
  equipment_category: string;
  status: string;
  is_simulated: boolean;
  current_resistance_kg: number;
  target_resistance_kg: number;
  mac_address?: string;
  firmware_version?: string;
  created_at: string;
  updated_at: string;
}

interface IoTTelemetry {
  id: number;
  device_id: number;
  user_id: number;
  exercise_type: string;
  resistance_kg: number;
  repetition_count: number;
  session_duration_seconds: number;
  intensity_score: number;
  heart_rate_bpm?: number;
  operational_state: string;
  timestamp: string;
}

interface SmartRecommendation {
  recommendation_type: string;
  title: string;
  message: string;
  action_suggested?: string;
  target_device_uid?: string;
  suggested_value?: number;
  confidence_score: number;
}

interface SmartAssistantResponse {
  user_id: number;
  total_active_devices: number;
  recommendations: SmartRecommendation[];
  timestamp: string;
}

export default function SmartGymPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"devices" | "telemetry" | "assistant">("devices");
  
  const [devices, setDevices] = useState<IoTDevice[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<IoTDevice | null>(null);
  const [telemetryHistory, setTelemetryHistory] = useState<IoTTelemetry[]>([]);
  const [assistantData, setAssistantData] = useState<SmartAssistantResponse | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [resistanceInput, setResistanceInput] = useState<number>(50);
  const [actionMessage, setActionMessage] = useState("");

  const getAuthToken = () => localStorage.getItem("access_token") || localStorage.getItem("token");

  useEffect(() => {
    fetchInitialIoTData();
  }, []);

  async function fetchInitialIoTData() {
    setLoading(true);
    setError("");
    const token = getAuthToken();
    if (!token) {
      router.push("/login?redirect=/iot");
      return;
    }

    try {
      // 1. Fetch User Devices
      const devRes = await fetch(`${API_BASE_URL}/iot/devices`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (devRes.status === 401) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("token");
        router.push("/login?redirect=/iot");
        return;
      }
      if (!devRes.ok) throw new Error("Failed to load smart gym devices.");
      const devData: IoTDevice[] = await devRes.json();
      setDevices(devData);

      if (devData.length > 0) {
        setSelectedDevice(devData[0]);
        setResistanceInput(devData[0].current_resistance_kg || 50);
        fetchTelemetryForDevice(devData[0].id, token);
      }

      // 2. Fetch Smart Assistant Recommendations
      const assistRes = await fetch(`${API_BASE_URL}/iot/assistant/recommendations`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (assistRes.ok) {
        const assistJson: SmartAssistantResponse = await assistRes.json();
        setAssistantData(assistJson);
      }
    } catch (err: any) {
      setError(err.message || "IoT Service communication error.");
    } finally {
      setLoading(false);
    }
  }

  async function fetchTelemetryForDevice(deviceId: number, token?: string) {
    const authToken = token || getAuthToken();
    if (!authToken) return;

    try {
      const res = await fetch(`${API_BASE_URL}/iot/devices/${deviceId}/telemetry?limit=15`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (res.ok) {
        const history: IoTTelemetry[] = await res.json();
        setTelemetryHistory(history);
      }
    } catch (err) {
      console.error("Telemetry fetch error", err);
    }
  }

  async function handleSendResistanceCommand(commandType: string, customVal?: number) {
    if (!selectedDevice) return;
    setActionMessage("");
    const token = getAuthToken();
    if (!token) return;

    const val = customVal !== undefined ? customVal : resistanceInput;

    try {
      const res = await fetch(`${API_BASE_URL}/iot/devices/${selectedDevice.id}/command`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          command_type: commandType,
          target_resistance_kg: val,
          step_increment_kg: 2.5,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || "Command execution failed.");
      }

      const cmdResp = await res.json();
      setActionMessage(`✓ Command '${commandType}' executed! New Resistance: ${cmdResp.target_resistance_kg} kg`);
      
      // Update local state
      const updatedDevices = devices.map((d) =>
        d.id === selectedDevice.id
          ? { ...d, current_resistance_kg: cmdResp.current_resistance_kg, target_resistance_kg: cmdResp.target_resistance_kg }
          : d
      );
      setDevices(updatedDevices);
      setSelectedDevice((prev) => prev ? { ...prev, current_resistance_kg: cmdResp.current_resistance_kg } : null);
    } catch (err: any) {
      setActionMessage(`❌ Error: ${err.message}`);
    }
  }

  async function handleSimulateTelemetryEvent() {
    if (!selectedDevice) return;
    setActionMessage("");
    const token = getAuthToken();
    if (!token) return;

    try {
      const res = await fetch(`${API_BASE_URL}/iot/simulation/generate/${selectedDevice.id}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) throw new Error("Simulation trigger failed.");
      const newTelem: IoTTelemetry = await res.json();
      
      setActionMessage(`⚡ Simulated Telemetry Event Ingested! Reps: ${newTelem.repetition_count}, Intensity: ${newTelem.intensity_score}%`);
      fetchTelemetryForDevice(selectedDevice.id, token);
    } catch (err: any) {
      setActionMessage(`❌ Error: ${err.message}`);
    }
  }

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-white">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-cyan-500 border-t-transparent"></div>
          <p className="text-slate-400 text-sm">Synchronizing Smart Gym IoT devices & telemetry...</p>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-white p-6">
        <div className="max-w-md rounded-2xl border border-red-900 bg-slate-900 p-8 text-center shadow-xl">
          <h1 className="text-2xl font-bold text-red-400">IoT Service Error</h1>
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

  return (
    <main className="min-h-screen bg-slate-950 text-white p-6 md:p-10">
      <div className="mx-auto max-w-6xl space-y-8">
        
        {/* Header Bar */}
        <header className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-cyan-950 border border-cyan-500/50 px-3 py-0.5 text-xs font-semibold text-cyan-300">
                Smart Gym IoT Integration
              </span>
              <span className="rounded-full bg-slate-900 border border-slate-800 px-3 py-0.5 text-[11px] text-slate-400">
                MQTT Topic Architecture
              </span>
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight mt-2 text-white">
              Smart Gym Equipment Intelligence
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              Connected equipment telemetry, safe resistance interfaces, and real-time rest/intensity heuristics.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push("/dashboard")}
              className="rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-medium hover:bg-slate-800 transition"
            >
              Dashboard
            </button>
          </div>
        </header>

        {/* Tab Navigation */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => setActiveTab("devices")}
            className={`px-5 py-2.5 text-sm font-bold rounded-xl transition ${
              activeTab === "devices"
                ? "bg-cyan-600 text-white shadow-lg shadow-cyan-600/30"
                : "bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-white"
            }`}
          >
            📡 Connected Devices ({devices.length})
          </button>

          <button
            onClick={() => setActiveTab("telemetry")}
            className={`px-5 py-2.5 text-sm font-bold rounded-xl transition ${
              activeTab === "telemetry"
                ? "bg-cyan-600 text-white shadow-lg shadow-cyan-600/30"
                : "bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-white"
            }`}
          >
            📊 Telemetry Stream ({telemetryHistory.length})
          </button>

          <button
            onClick={() => setActiveTab("assistant")}
            className={`px-5 py-2.5 text-sm font-bold rounded-xl transition ${
              activeTab === "assistant"
                ? "bg-cyan-600 text-white shadow-lg shadow-cyan-600/30"
                : "bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-white"
            }`}
          >
            🤖 Smart Assistant Heuristics ({assistantData?.recommendations.length || 0})
          </button>
        </div>

        {/* TAB 1: CONNECTED DEVICES */}
        {activeTab === "devices" && (
          <div className="grid gap-6 md:grid-cols-3">
            {/* Left Device Selection */}
            <div className="space-y-4">
              <h2 className="text-lg font-bold text-white flex items-center justify-between">
                <span>Equipment Inventory</span>
                <span className="text-xs font-normal text-slate-400">Sample Demo Devices</span>
              </h2>

              <div className="space-y-3">
                {devices.map((dev) => (
                  <button
                    key={dev.id}
                    onClick={() => {
                      setSelectedDevice(dev);
                      setResistanceInput(dev.current_resistance_kg);
                      fetchTelemetryForDevice(dev.id);
                    }}
                    className={`w-full text-left rounded-2xl border p-4 transition flex flex-col justify-between ${
                      selectedDevice?.id === dev.id
                        ? "border-cyan-500 bg-cyan-950/30 shadow-lg shadow-cyan-950/50"
                        : "border-slate-800 bg-slate-900 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <h3 className="font-bold text-white text-sm">{dev.device_name}</h3>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        dev.status === "active"
                          ? "bg-emerald-950 text-emerald-300 border border-emerald-500/40"
                          : "bg-slate-800 text-slate-300"
                      }`}>
                        {dev.status.toUpperCase()}
                      </span>
                    </div>

                    <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
                      <span>Category: <strong className="text-slate-200 capitalize">{dev.equipment_category.replace("_", " ")}</strong></span>
                      <span className="font-semibold text-cyan-300">{dev.current_resistance_kg} kg</span>
                    </div>

                    <div className="mt-2 text-[10px] text-slate-500 italic">
                      UID: {dev.device_uid} • {dev.is_simulated ? "Sample Demo Device" : "Hardware Connected"}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Right Control Interface */}
            {selectedDevice && (
              <div className="md:col-span-2 rounded-2xl border border-slate-800 bg-slate-900 p-6 space-y-6 shadow-xl">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b border-slate-800 pb-4 gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-xl font-bold text-white">{selectedDevice.device_name}</h2>
                      <span className="rounded-full bg-slate-800 border border-slate-700 px-2.5 py-0.5 text-[10px] font-semibold text-slate-300">
                        {selectedDevice.is_simulated ? "Sample Demo IoT Device" : "Real Hardware"}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">
                      MQTT Topic: <code className="text-cyan-400">gym/1/device/{selectedDevice.device_uid}/command</code>
                    </p>
                  </div>

                  <button
                    onClick={handleSimulateTelemetryEvent}
                    className="rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-500 transition shadow-md"
                  >
                    ⚡ Simulate Telemetry Set
                  </button>
                </div>

                {actionMessage && (
                  <div className="rounded-xl border border-slate-700 bg-slate-950 p-3 text-xs font-medium text-cyan-300">
                    {actionMessage}
                  </div>
                )}

                {/* Resistance Control Interface */}
                <div className="space-y-4 rounded-xl border border-slate-800 bg-slate-950 p-5">
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    Equipment Resistance Interface
                  </h3>

                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400">Current Load:</span>
                    <span className="text-2xl font-extrabold text-cyan-400">{selectedDevice.current_resistance_kg} kg</span>
                  </div>

                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
                      <span>Set Target Load (kg):</span>
                      <span className="text-cyan-400 font-bold">{resistanceInput} kg</span>
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="200"
                      step="2.5"
                      value={resistanceInput}
                      onChange={(e) => setResistanceInput(parseFloat(e.target.value))}
                      className="w-full accent-cyan-500 bg-slate-800"
                    />
                  </div>

                  <div className="flex flex-wrap items-center gap-2 pt-2">
                    <button
                      onClick={() => handleSendResistanceCommand("set_resistance")}
                      className="rounded-lg bg-cyan-600 px-4 py-2 text-xs font-bold text-white hover:bg-cyan-500 transition"
                    >
                      Apply Target Load
                    </button>

                    <button
                      onClick={() => handleSendResistanceCommand("increase_resistance")}
                      className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800 transition"
                    >
                      + 2.5 kg
                    </button>

                    <button
                      onClick={() => handleSendResistanceCommand("decrease_resistance")}
                      className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800 transition"
                    >
                      - 2.5 kg
                    </button>

                    <button
                      onClick={() => handleSendResistanceCommand("emergency_stop")}
                      className="rounded-lg bg-red-950 border border-red-600/60 px-3 py-2 text-xs font-bold text-red-300 hover:bg-red-900 transition ml-auto"
                    >
                      🛑 Emergency Stop
                    </button>
                  </div>
                </div>

                {/* Device Telemetry Preview */}
                <div className="space-y-3">
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    Recent Performance Telemetry
                  </h3>

                  {telemetryHistory.length === 0 ? (
                    <p className="text-xs text-slate-500 italic">No telemetry recorded for this equipment yet.</p>
                  ) : (
                    <div className="space-y-2">
                      {telemetryHistory.slice(0, 3).map((t) => (
                        <div key={t.id} className="flex items-center justify-between rounded-lg bg-slate-950 border border-slate-800/80 p-3 text-xs">
                          <div>
                            <span className="font-semibold text-white">{t.exercise_type}</span>
                            <div className="text-[11px] text-slate-400 mt-0.5">
                              Load: {t.resistance_kg}kg • Reps: {t.repetition_count} • HR: {t.heart_rate_bpm ? `${t.heart_rate_bpm} BPM` : "N/A"}
                            </div>
                          </div>
                          <div className="text-right">
                            <span className="font-bold text-cyan-400">{t.intensity_score}% Intensity</span>
                            <div className="text-[10px] text-slate-500">{new Date(t.timestamp).toLocaleTimeString()}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: TELEMETRY STREAM */}
        {activeTab === "telemetry" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between rounded-2xl border border-slate-800 bg-slate-900 p-4">
              <div className="text-xs text-slate-300">
                MQTT Payload Schema: <code className="text-cyan-400 font-mono">{"{ device_id, resistance_kg, repetition_count, intensity_score, heart_rate_bpm }"}</code>
              </div>
              <span className="text-xs font-bold text-cyan-300">Node-RED Compatible</span>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900 overflow-hidden shadow-xl">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="border-b border-slate-800 bg-slate-950 text-slate-400 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="p-4">Timestamp</th>
                    <th className="p-4">Exercise</th>
                    <th className="p-4">Resistance (kg)</th>
                    <th className="p-4">Reps</th>
                    <th className="p-4">Intensity Score</th>
                    <th className="p-4">Heart Rate</th>
                    <th className="p-4">State</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {telemetryHistory.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="p-6 text-center text-slate-500 italic">
                        No telemetry logs available. Select an equipment device and trigger a set simulation.
                      </td>
                    </tr>
                  ) : (
                    telemetryHistory.map((t) => (
                      <tr key={t.id} className="hover:bg-slate-800/40 transition">
                        <td className="p-4 text-slate-400">{new Date(t.timestamp).toLocaleString()}</td>
                        <td className="p-4 font-semibold text-white">{t.exercise_type}</td>
                        <td className="p-4 font-bold text-cyan-300">{t.resistance_kg} kg</td>
                        <td className="p-4">{t.repetition_count} reps</td>
                        <td className="p-4">
                          <span className="rounded-full bg-cyan-950 border border-cyan-500/40 px-2 py-0.5 text-[11px] font-bold text-cyan-300">
                            {t.intensity_score}%
                          </span>
                        </td>
                        <td className="p-4">{t.heart_rate_bpm ? `❤️ ${t.heart_rate_bpm} BPM` : "—"}</td>
                        <td className="p-4 capitalize text-slate-400">{t.operational_state}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 3: SMART ASSISTANT HEURISTICS */}
        {activeTab === "assistant" && (
          <div className="space-y-6">
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 space-y-4">
              <h2 className="text-xl font-bold text-white flex items-center justify-between">
                <span>🤖 Smart Gym Assistant Intelligence</span>
                <span className="text-xs font-normal text-slate-400">Grounded Application Rules</span>
              </h2>

              <p className="text-xs text-slate-400">
                The Smart Gym Assistant continuously monitors equipment state, set intensity, and heart rate telemetry to suggest safe recovery rest intervals and progressive overload load increases.
              </p>

              <div className="grid gap-4 md:grid-cols-2">
                {assistantData?.recommendations.map((rec, idx) => (
                  <div
                    key={idx}
                    className="rounded-xl border border-slate-800 bg-slate-950 p-5 space-y-3 flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2">
                        <h3 className="font-bold text-white text-sm">{rec.title}</h3>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          rec.recommendation_type === "fatigue_alert"
                            ? "bg-red-950 text-red-300 border border-red-500/40"
                            : rec.recommendation_type === "rest_interval"
                            ? "bg-amber-950 text-amber-300 border border-amber-500/40"
                            : "bg-cyan-950 text-cyan-300 border border-cyan-500/40"
                        }`}>
                          {rec.recommendation_type.replace("_", " ").toUpperCase()}
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 mt-2 leading-relaxed">{rec.message}</p>
                    </div>

                    {rec.action_suggested && (
                      <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
                        <span className="text-[11px] text-slate-400">Rule Confidence: {(rec.confidence_score * 100).toFixed(0)}%</span>
                        <span className="rounded-md bg-cyan-900/50 border border-cyan-500/40 px-3 py-1 text-xs font-bold text-cyan-200">
                          {rec.action_suggested}
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

      </div>
    </main>
  );
}

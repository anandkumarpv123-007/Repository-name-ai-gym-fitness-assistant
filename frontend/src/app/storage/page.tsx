"use client";

import { useEffect, useState, ChangeEvent } from "react";
import { useRouter } from "next/navigation";
import { API_BASE_URL } from "@/api/config";

interface MediaAsset {
  id: number;
  user_id: number;
  file_name: string;
  stored_file_name: string;
  file_type: string;
  mime_type: string;
  file_size_bytes: number;
  storage_provider: string;
  storage_key: string;
  public_url: string;
  category: string;
  created_at: string;
  updated_at: string;
  is_deleted: boolean;
}

interface StorageStats {
  user_id: number;
  total_files: number;
  total_bytes: number;
  total_mb: number;
  max_file_size_mb: number;
  allowed_mime_types: string[];
  supported_providers: string[];
}

export default function StoragePage() {
  const router = useRouter();
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [stats, setStats] = useState<StorageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Form State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [category, setCategory] = useState("general");
  const [storageProvider, setStorageProvider] = useState("local");
  const [filterCategory, setFilterCategory] = useState("all");

  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

  useEffect(() => {
    if (!token) {
      router.push("/login");
      return;
    }
    loadData();
  }, [token]);

  async function loadData() {
    setLoading(true);
    setError(null);

    try {
      const [assetsRes, statsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/media/assets`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_BASE_URL}/media/stats`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      if (assetsRes.status === 401 || statsRes.status === 401) {
        localStorage.removeItem("access_token");
        router.push("/login");
        return;
      }

      if (!assetsRes.ok) throw new Error("Failed to load media assets.");
      if (!statsRes.ok) throw new Error("Failed to load storage statistics.");

      const assetsData = await assetsRes.json();
      const statsData = await statsRes.json();

      setAssets(assetsData);
      setStats(statsData);
    } catch (err: any) {
      setError(err.message || "An error occurred while loading media storage.");
    } finally {
      setLoading(false);
    }
  }

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedFile) {
      setError("Please select a file to upload.");
      return;
    }

    setUploading(true);
    setError(null);
    setSuccessMsg(null);

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("category", category);
    formData.append("storage_provider", storageProvider);

    try {
      const res = await fetch(`${API_BASE_URL}/media/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Upload failed.");
      }

      setSuccessMsg(`File "${data.file_name}" uploaded successfully!`);
      setSelectedFile(null);
      // Reset input element value
      const fileInput = document.getElementById("file-input") as HTMLInputElement;
      if (fileInput) fileInput.value = "";

      await loadData();
    } catch (err: any) {
      setError(err.message || "File upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function handleDownload(storedFileName: string, fileName: string) {
    try {
      const res = await fetch(`${API_BASE_URL}/media/file/${storedFileName}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to download media file.");
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err.message || "Download failed.");
    }
  }

  async function handleDelete(assetId: number, permanent = false) {
    if (!confirm(`Are you sure you want to delete this asset?`)) return;

    try {
      const res = await fetch(`${API_BASE_URL}/media/assets/${assetId}?permanent=${permanent}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to delete file.");
      }

      setSuccessMsg("Asset deleted successfully.");
      await loadData();
    } catch (err: any) {
      setError(err.message || "Deletion failed.");
    }
  }

  function formatBytes(bytes: number) {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  }

  const filteredAssets = assets.filter((asset) => {
    if (filterCategory === "all") return true;
    return asset.category === filterCategory;
  });

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-white">
        <p className="text-slate-400">Loading Storage & Media Manager...</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 p-6 md:p-8 text-white">
      {/* Navigation & Header */}
      <header className="mx-auto flex max-w-6xl items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-teal-400 to-blue-400 bg-clip-text text-transparent">
            Media & Storage Infrastructure
          </h1>
          <p className="mt-1 text-slate-400 text-sm">
            Centralized file uploads, cloud storage simulation, and asset management
          </p>
        </div>

        <button
          onClick={() => router.push("/dashboard")}
          className="rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-medium hover:bg-slate-800 transition"
        >
          ← Back to Dashboard
        </button>
      </header>

      {/* Notifications */}
      <div className="mx-auto max-w-6xl mt-6">
        {error && (
          <div className="mb-4 rounded-xl border border-red-900 bg-red-950/40 p-4 text-red-300 text-sm">
            ⚠️ {error}
          </div>
        )}
        {successMsg && (
          <div className="mb-4 rounded-xl border border-emerald-900 bg-emerald-950/40 p-4 text-emerald-300 text-sm">
            ✅ {successMsg}
          </div>
        )}
      </div>

      {/* Stats Summary Cards */}
      <section className="mx-auto mt-2 grid max-w-6xl gap-4 md:grid-cols-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <p className="text-xs text-slate-400 font-medium uppercase">Total Assets</p>
          <p className="mt-2 text-3xl font-bold text-teal-400">{stats?.total_files ?? 0}</p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <p className="text-xs text-slate-400 font-medium uppercase">Storage Used</p>
          <p className="mt-2 text-3xl font-bold text-blue-400">
            {stats ? `${stats.total_mb} MB` : "0 MB"}
          </p>
          <p className="text-xs text-slate-500 mt-1">({stats ? formatBytes(stats.total_bytes) : "0 Bytes"})</p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <p className="text-xs text-slate-400 font-medium uppercase">Max Per-File Size</p>
          <p className="mt-2 text-3xl font-bold text-indigo-400">
            {stats?.max_file_size_mb ?? 50} MB
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <p className="text-xs text-slate-400 font-medium uppercase">Storage Modes</p>
          <div className="mt-2 flex flex-wrap gap-1">
            <span className="rounded bg-teal-950 border border-teal-700 px-2 py-0.5 text-xs text-teal-300 font-medium">Local</span>
            <span className="rounded bg-blue-950 border border-blue-700 px-2 py-0.5 text-xs text-blue-300 font-medium">S3 Sim</span>
            <span className="rounded bg-purple-950 border border-purple-700 px-2 py-0.5 text-xs text-purple-300 font-medium">GCS Sim</span>
          </div>
        </div>
      </section>

      {/* Upload Section */}
      <section className="mx-auto mt-6 max-w-6xl rounded-xl border border-slate-800 bg-slate-900 p-6">
        <h2 className="text-xl font-semibold mb-4 text-white">Upload New Asset</h2>

        <form onSubmit={handleUpload} className="grid gap-4 md:grid-cols-4 items-end">
          <div className="md:col-span-2">
            <label className="block text-xs text-slate-400 mb-1">Select File (Max 50MB)</label>
            <input
              id="file-input"
              type="file"
              onChange={handleFileChange}
              className="w-full text-sm text-slate-300 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-teal-900/60 file:text-teal-300 hover:file:bg-teal-800/80 cursor-pointer border border-slate-700 rounded-lg p-1 bg-slate-950"
            />
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-teal-500"
            >
              <option value="general">General</option>
              <option value="workout_video">Workout Video</option>
              <option value="pose_image">Pose Image</option>
              <option value="meal_photo">Meal Photo</option>
              <option value="report">Report / Doc</option>
            </select>
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Storage Provider</label>
            <select
              value={storageProvider}
              onChange={(e) => setStorageProvider(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-teal-500"
            >
              <option value="local">Local Storage</option>
              <option value="s3_simulation">AWS S3 (Simulated)</option>
              <option value="gcs_simulation">Google Cloud (Simulated)</option>
            </select>
          </div>

          <div className="md:col-span-4 flex justify-end">
            <button
              type="submit"
              disabled={uploading || !selectedFile}
              className="rounded-lg bg-gradient-to-r from-teal-600 to-blue-600 px-6 py-2 text-sm font-semibold text-white hover:from-teal-500 hover:to-blue-500 disabled:opacity-50 transition"
            >
              {uploading ? "Uploading..." : "Upload Asset"}
            </button>
          </div>
        </form>
      </section>

      {/* Media Assets Gallery */}
      <section className="mx-auto mt-6 max-w-6xl rounded-xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between mb-4 gap-4">
          <h2 className="text-xl font-semibold text-white">Stored Media Assets</h2>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Filter Category:</span>
            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-slate-200"
            >
              <option value="all">All Categories</option>
              <option value="general">General</option>
              <option value="workout_video">Workout Video</option>
              <option value="pose_image">Pose Image</option>
              <option value="meal_photo">Meal Photo</option>
              <option value="report">Report / Doc</option>
            </select>
          </div>
        </div>

        {filteredAssets.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-800 p-8 text-center text-slate-500">
            No media assets found. Upload a file above to get started.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="border-b border-slate-800 bg-slate-950 text-xs uppercase text-slate-400">
                <tr>
                  <th className="px-4 py-3">Asset</th>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3">Provider</th>
                  <th className="px-4 py-3">Size</th>
                  <th className="px-4 py-3">Uploaded</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {filteredAssets.map((asset) => (
                  <tr key={asset.id} className="hover:bg-slate-800/40">
                    <td className="px-4 py-3">
                      <p className="font-medium text-white truncate max-w-xs">{asset.file_name}</p>
                      <p className="text-xs text-slate-500 font-mono">{asset.mime_type}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-300 border border-slate-700">
                        {asset.category}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded px-2 py-0.5 text-xs font-medium border ${
                          asset.storage_provider === "s3_simulation"
                            ? "bg-blue-950 text-blue-300 border-blue-800"
                            : asset.storage_provider === "gcs_simulation"
                            ? "bg-purple-950 text-purple-300 border-purple-800"
                            : "bg-teal-950 text-teal-300 border-teal-800"
                        }`}
                      >
                        {asset.storage_provider}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-400">{formatBytes(asset.file_size_bytes)}</td>
                    <td className="px-4 py-3 text-slate-400 text-xs">
                      {new Date(asset.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right space-x-2">
                      <button
                        onClick={() => handleDownload(asset.stored_file_name, asset.file_name)}
                        className="rounded bg-slate-800 px-2.5 py-1 text-xs font-medium text-teal-300 hover:bg-slate-700 transition inline-block"
                      >
                        Download / View
                      </button>
                      <button
                        onClick={() => handleDelete(asset.id, false)}
                        className="rounded bg-red-950/60 border border-red-800 px-2.5 py-1 text-xs font-medium text-red-300 hover:bg-red-900 transition"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}

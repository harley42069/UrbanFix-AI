"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { getCurrentUser, login, rememberAuthSession } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";

export default function LoginPage() {
  const router = useRouter();
  const { pushToast } = useToast();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"citizen" | "admin">("citizen");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    if (activeTab === "citizen") {
      router.push("/signalements/new");
      return;
    }

    if (activeTab === "admin") {
      if (!username || !password) {
        setError("Email/username and password are required");
        setLoading(false);
        return;
      }
    }

    try {
      const session = await login({ username, password });
      rememberAuthSession(session, null);
      const user = await getCurrentUser();
      rememberAuthSession(session, user);
      pushToast({
        title: "Login successful",
        message: `Welcome ${user.full_name}`,
        variant: "success"
      });
      router.push("/dashboard");
    } catch (submitError) {
      const message = submitError instanceof Error ? submitError.message : "Unable to log in";
      setError(message);
      pushToast({ title: "Login failed", message, variant: "danger" });
    } finally {
      setLoading(false);
    }
  }

  return (
    <section
      className="flex min-h-[calc(100vh-140px)] items-center justify-center px-4 py-12"
      style={{ background: "linear-gradient(180deg, #fdf6ec 0%, #f5ede0 100%)" }}
    >
      <div className="w-full max-w-md rounded-3xl border border-[#e8d5c0] bg-white p-8 shadow-lg">
        <div className="text-center">
          <p className="text-2xl font-bold text-[#c4623a]">UrbanFix AI</p>
          <div
            className={`mt-2 inline-flex rounded-full px-4 py-1 text-xs font-semibold text-white ${
              activeTab === "citizen" ? "bg-[#c4623a]" : "bg-[#1a5490]"
            }`}
          >
            {activeTab === "citizen" ? "Citizen Space" : "Municipal Space"}
          </div>
        </div>

        <div className="my-6 border-t border-[#e8d5c0]" />

        <div className="flex border-b border-[#e8d5c0] text-sm font-semibold">
          <button
            type="button"
            onClick={() => { setActiveTab("citizen"); setError(null); }}
            className={`flex-1 pb-3 text-center transition ${
              activeTab === "citizen"
                ? "border-b-2 border-[#c4623a] text-[#c4623a]"
                : "text-[#8b6f5e]"
            }`}
          >
            Citizen Space
          </button>
          <button
            type="button"
            onClick={() => { setActiveTab("admin"); setError(null); }}
            className={`flex-1 pb-3 text-center transition ${
              activeTab === "admin"
                ? "border-b-2 border-[#c4623a] text-[#c4623a]"
                : "text-[#8b6f5e]"
            }`}
          >
            Municipal Space
          </button>
        </div>

        <div className="pt-6">
          {activeTab === "citizen" ? (
            <div className="space-y-6 text-center">
              <div>
                <p className="text-sm font-semibold text-[#1a1a1a]">No account required</p>
                <p className="mt-2 text-sm text-[#8b6f5e]">Submit a report directly</p>
              </div>
              <button
                type="button"
                onClick={() => router.push("/signalements/new")}
                className="w-full rounded-full bg-[#c4623a] px-4 py-3 text-sm font-semibold text-white transition hover:bg-[#a94a2a] disabled:cursor-not-allowed disabled:opacity-60"
              >
                Submit a report
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <label className="block space-y-2">
                <span className="text-sm font-medium text-[#1a1a1a]">Username</span>
                <input
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  className="w-full rounded-3xl border border-[#e8d5c0] bg-white px-4 py-3 text-[#1a1a1a] outline-none transition focus:border-[#c4623a] focus:ring-4 focus:ring-[#f3d6c8]"
                  placeholder="agent@urbanfix.local"
                  autoComplete="username"
                />
              </label>

              <label className="block space-y-2">
                <span className="text-sm font-medium text-[#1a1a1a]">Password</span>
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="w-full rounded-3xl border border-[#e8d5c0] bg-white px-4 py-3 text-[#1a1a1a] outline-none transition focus:border-[#c4623a] focus:ring-4 focus:ring-[#f3d6c8]"
                  placeholder="********"
                  autoComplete="current-password"
                />
              </label>

              {error ? <p className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</p> : null}

              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-full bg-[#c4623a] px-4 py-3 text-sm font-semibold text-white transition hover:bg-[#a94a2a] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "Logging in..." : "Log in"}
              </button>
            </form>
          )}
        </div>
      </div>
    </section>
  );
}

"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

const STEPS = ["ICP", "Sourcing", "Enrichment", "Signals", "Scoring", "Outreach", "Export"];

function scoreColor(score: number, dark: boolean) {
  if (score >= 65) return dark ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" : "bg-emerald-100 text-emerald-700 border-emerald-200";
  if (score >= 45) return dark ? "bg-amber-500/15 text-amber-400 border-amber-500/30" : "bg-amber-100 text-amber-700 border-amber-200";
  return dark ? "bg-rose-500/15 text-rose-400 border-rose-500/30" : "bg-rose-100 text-rose-700 border-rose-200";
}

export default function Home() {
  const [dark, setDark] = useState(false);  
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [results, setResults] = useState<any[]>([]);

  const [icp, setIcp] = useState({
    industry: "SaaS",
    company_size: "50-200",
    location: "France",
    job_titles: "CTO, VP Sales",
    keywords: "B2B, cloud",
  });

  const addLog = (msg: string) => setLogs((prev) => [...prev, msg]);

  async function startPipeline() {
    setLoading(true);
    setLogs([]);
    setResults([]);
    setCurrentStep(0);
    try {
      const sessionRes = await fetch(`${API}/sessions/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: `Session ${Date.now()}` }),
      });
      const session = await sessionRes.json();
      const sid = session.id;
      setSessionId(sid);
      addLog(`Session #${sid} created`);
      setCurrentStep(1);

      await fetch(`${API}/sessions/${sid}/icp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          industry: icp.industry,
          company_size: icp.company_size,
          location: icp.location,
          job_titles: icp.job_titles.split(",").map((s) => s.trim()),
          keywords: icp.keywords.split(",").map((s) => s.trim()),
        }),
      });
      addLog("ICP profile defined");
      setCurrentStep(2);

      await fetch(`${API}/sessions/${sid}/sourcing?count=15`, { method: "POST" });
      addLog("Sourcing completed — 15 accounts identified");
      setCurrentStep(3);

      await fetch(`${API}/sessions/${sid}/enrichment`, { method: "POST" });
      addLog("Enrichment cascade completed (with fallback handling)");
      setCurrentStep(4);

      await fetch(`${API}/sessions/${sid}/signals`, { method: "POST" });
      addLog("Buying signals detected");
      setCurrentStep(5);

      await fetch(`${API}/sessions/${sid}/scoring`, { method: "POST" });
      addLog("Accounts scored & ranked");
      setCurrentStep(6);

      await fetch(`${API}/sessions/${sid}/outreach`, { method: "POST" });
      addLog("AI-personalized outreach generated");
      setCurrentStep(7);

      const exportRes = await fetch(`${API}/sessions/${sid}/export/preview`);
      const data = await exportRes.json();
      setResults(data);
      addLog("Pipeline complete — results ready");
    } catch (err) {
      addLog(`Error: ${err}`);
    } finally {
      setLoading(false);
    }
  }

  const downloadCSV = () => sessionId && window.open(`${API}/sessions/${sessionId}/export/csv`, "_blank");
  const downloadExcel = () => sessionId && window.open(`${API}/sessions/${sessionId}/export/excel`, "_blank");

  return (
    <div className={dark ? "dark" : ""}>
      <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900 transition-colors">
        {/* Header */}
        <div className="bg-gradient-to-r from-slate-900 to-indigo-900 dark:from-slate-950 dark:to-indigo-950 text-white relative">
          <div className="max-w-6xl mx-auto px-8 py-10">
            <button
              onClick={() => setDark(!dark)}
              className="absolute top-6 right-8 bg-white/10 hover:bg-white/20 text-white text-sm font-medium px-3 py-2 rounded-lg transition flex items-center gap-2"
            >
              {dark ? "☀️ Light" : "🌙 Dark"}
            </button>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center text-xl">⚡</div>
              <h1 className="text-3xl font-bold tracking-tight">PulseDev</h1>
              <span className="text-xs font-medium bg-white/10 px-2 py-1 rounded-full text-indigo-200">B2B GTM Engine</span>
            </div>
            <p className="text-indigo-200 text-sm">
              ICP → Sourcing → Enrichment → Signal Detection → Scoring → AI Outreach → Export
            </p>
            <p className="text-indigo-200/70 text-sm mt-4 max-w-3xl leading-relaxed">
              PulseDev automatise l'ensemble du pipeline de prospection B2B : à partir d'un profil client idéal,
              la plateforme identifie automatiquement des comptes correspondants, enrichit leurs données via un
              système de sources multiples avec repli automatique, détecte leurs signaux d'achat réels, les classe
              par pertinence, puis génère des séquences d'outreach personnalisées grâce à l'IA — prêtes à être
              exportées en un clic.
            </p>
          </div>
        </div>

        <div className="max-w-6xl mx-auto px-8 -mt-6 pb-16 relative z-10">
          {/* ICP Form */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl shadow-slate-200/50 dark:shadow-black/20 p-8 mb-6 border border-slate-100 dark:border-slate-800 transition-colors">
            <div className="flex items-center gap-2 mb-6">
              <span className="w-6 h-6 rounded-full bg-indigo-600 text-white text-xs font-bold flex items-center justify-center">1</span>
              <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Define your Ideal Customer Profile</h2>
            </div>

            <div className="grid grid-cols-2 gap-5">
              {[
                { label: "Industry", key: "industry" },
                { label: "Company Size", key: "company_size" },
                { label: "Location", key: "location" },
                { label: "Job Titles (comma-separated)", key: "job_titles" },
              ].map((field) => (
                <div key={field.key}>
                  <label className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1.5 uppercase tracking-wide">
                    {field.label}
                  </label>
                  <input
                    className="w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 rounded-lg px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
                    value={(icp as any)[field.key]}
                    onChange={(e) => setIcp({ ...icp, [field.key]: e.target.value })}
                  />
                </div>
              ))}
            </div>

            <button
              onClick={startPipeline}
              disabled={loading}
              className="mt-7 bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-xl font-semibold text-sm shadow-lg shadow-indigo-600/30 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center gap-2"
            >
              {loading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  Running pipeline...
                </>
              ) : (
                <>🚀 Launch New Session</>
              )}
            </button>
          </div>

          {/* Progress Tracker */}
          {sessionId && (
            <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl shadow-slate-200/50 dark:shadow-black/20 p-8 mb-6 border border-slate-100 dark:border-slate-800 transition-colors">
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Pipeline Progress</h2>
                <span className="text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 px-3 py-1 rounded-full">
                  Session #{sessionId}
                </span>
              </div>

              <div className="flex gap-1.5 mb-5">
                {STEPS.map((step, i) => (
                  <div key={step} className="flex-1">
                    <div
                      className={`h-1.5 rounded-full mb-2 transition-all duration-500 ${
                        i < currentStep
                          ? "bg-emerald-500"
                          : i === currentStep && loading
                          ? "bg-indigo-500 animate-pulse"
                          : "bg-slate-200 dark:bg-slate-700"
                      }`}
                    />
                    <p className={`text-[11px] text-center font-medium ${
                      i < currentStep ? "text-emerald-600 dark:text-emerald-400" : i === currentStep && loading ? "text-indigo-600 dark:text-indigo-400" : "text-slate-400 dark:text-slate-600"
                    }`}>
                      {step}
                    </p>
                  </div>
                ))}
              </div>

              <div className="bg-slate-900 dark:bg-black rounded-xl p-4 max-h-40 overflow-y-auto">
                {logs.map((log, i) => (
                  <div key={i} className="text-[13px] font-mono text-emerald-400 py-0.5 flex items-start gap-2">
                    <span className="text-slate-500">›</span> {log}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Results */}
          {results.length > 0 && (
            <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl shadow-slate-200/50 dark:shadow-black/20 p-8 border border-slate-100 dark:border-slate-800 transition-colors">
              <div className="flex justify-between items-center mb-6">
                <div>
                  <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Ranked Prospects</h2>
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">{results.length} accounts scored and ready for outreach</p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={downloadCSV}
                    className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 px-4 py-2 rounded-lg text-sm font-medium transition"
                  >
                    📄 CSV
                  </button>
                  <button
                    onClick={downloadExcel}
                    className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-sm font-medium shadow-lg shadow-emerald-600/20 transition"
                  >
                    📊 Excel
                  </button>
                </div>
              </div>

              <div className="overflow-x-auto -mx-2">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[11px] uppercase tracking-wide text-slate-400 dark:text-slate-500 border-b border-slate-100 dark:border-slate-800">
                      <th className="py-3 px-2 font-medium">#</th>
                      <th className="py-3 px-2 font-medium">Company</th>
                      <th className="py-3 px-2 font-medium">Industry</th>
                      <th className="py-3 px-2 font-medium">Score</th>
                      <th className="py-3 px-2 font-medium">Outreach Preview</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((r: any) => (
                      <tr key={r.company_name} className="border-b border-slate-50 dark:border-slate-800/60 hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition">
                        <td className="py-3 px-2 font-semibold text-slate-400 dark:text-slate-500">{r.rank}</td>
                        <td className="py-3 px-2 font-medium text-slate-800 dark:text-slate-100">{r.company_name}</td>
                        <td className="py-3 px-2 text-slate-500 dark:text-slate-400">{r.industry}</td>
                        <td className="py-3 px-2">
                          <span className={`inline-block px-2.5 py-1 rounded-full text-xs font-semibold border ${scoreColor(r.total_score, dark)}`}>
                            {r.total_score}
                          </span>
                        </td>
                        <td className="py-3 px-2 text-slate-500 dark:text-slate-400 max-w-sm truncate">{r.outreach_message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
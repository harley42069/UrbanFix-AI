"use client";

import { useRouter } from "next/navigation";

export default function HomePage() {
  const router = useRouter();
  
  return (
    <div 
      className="min-h-[calc(100vh-140px)] w-full"
      style={{
        background: "linear-gradient(135deg, #fdf6ec 0%, #f5ede0 50%, #ede0cc 100%)",
        backgroundAttachment: "fixed"
      }}
    >
      {/* Subtle geometric pattern overlay */}
      <div 
        className="absolute inset-0 pointer-events-none opacity-5"
        style={{
          backgroundImage: "repeating-linear-gradient(90deg, transparent, transparent 50px, #1a1a1a 50px, #1a1a1a 51px)"
        }}
      />
      
      {/* Hero Section */}
      <div className="relative z-10 mx-auto w-full max-w-7xl px-4 py-16 sm:py-24 lg:px-8">
        <div className="space-y-8 text-center">
          <div className="inline-flex items-center justify-center w-full">
            <span className="rounded-full bg-[#c4623a] px-6 py-2 text-sm font-semibold text-white">
              Tunisian Urban Platform
            </span>
          </div>
          
          <div className="space-y-2">
            <h1 className="text-5xl sm:text-6xl font-black text-[#1a1a1a]">
              UrbanFix AI
            </h1>
            <p className="text-xl sm:text-2xl font-bold text-[#c4623a]">
              From field photo to PDF report
            </p>
          </div>
          
          <p className="mx-auto max-w-2xl text-base leading-7 text-slate-700 sm:text-lg">
            Automatically detect urban damage, generate photorealistic renovation scenarios,
            and get a budget estimate in Tunisian dinars.
          </p>
          
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={() => router.push("/signalements/new")}
              className="rounded-full bg-[#c4623a] px-8 py-3 text-base font-semibold text-white transition hover:bg-[#a94a2a]"
            >
              Submit a report
            </button>
            <button
              onClick={() => router.push("/login")}
              className="rounded-full border-2 border-[#c4623a] bg-white px-8 py-3 text-base font-semibold text-[#c4623a] transition hover:bg-[#fdf6ec]"
            >
              Admin workspace
            </button>
          </div>
        </div>
      </div>
      
      {/* Cards Section */}
      <div className="relative z-10 mx-auto w-full max-w-7xl px-4 py-12 lg:px-8">
        <div className="grid gap-8 xl:grid-cols-2">
          <button
            type="button"
            onClick={() => router.push("/signalements/new")}
            className="text-left rounded-3xl border border-[#e8d5c0] border-t-4 border-t-[#c4623a] bg-white p-8 shadow-lg space-y-6 cursor-pointer transition-transform duration-200 hover:scale-[1.01] hover:shadow-xl"
          >
            <div className="inline-flex rounded-full bg-[#c4623a] px-4 py-2 text-xs font-semibold uppercase tracking-wider text-white">
              CITIZEN SPACE
            </div>
            <h2 className="text-3xl font-bold text-slate-900">
              Report a problem
            </h2>
            <p className="text-base leading-6 text-slate-600">
              Take a photo and submit it in seconds.
              No account required.
            </p>
            <div className="flex justify-start gap-1 pt-4">
              <span className="text-[#c4623a] text-lg">◆</span>
              <span className="text-[#c4623a] text-lg">◆</span>
              <span className="text-[#c4623a] text-lg">◆</span>
            </div>
          </button>
          
          <button
            type="button"
            onClick={() => router.push("/login")}
            className="text-left rounded-3xl border border-[#e8d5c0] border-t-4 border-t-[#1a5490] bg-white p-8 shadow-lg space-y-6 cursor-pointer transition-transform duration-200 hover:scale-[1.01] hover:shadow-xl"
          >
            <div className="inline-flex rounded-full bg-[#1a5490] px-4 py-2 text-xs font-semibold uppercase tracking-wider text-white">
              MUNICIPAL SPACE
            </div>
            <h2 className="text-3xl font-bold text-slate-900">
              Manage reports
            </h2>
            <p className="text-base leading-6 text-slate-600">
              Admin dashboard with AI analysis, scenarios, and PDF reports.
            </p>
            <div className="flex justify-start gap-1 pt-4">
              <span className="text-[#1a5490] text-lg">◆</span>
              <span className="text-[#1a5490] text-lg">◆</span>
              <span className="text-[#1a5490] text-lg">◆</span>
            </div>
          </button>
        </div>
      </div>
      
    </div>
  );
}

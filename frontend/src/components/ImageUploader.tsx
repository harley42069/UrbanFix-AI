"use client";

import { useEffect, useMemo } from "react";

type ImageUploaderProps = {
  file: File | null;
  onChange: (file: File | null) => void;
  error?: string | null;
};

export default function ImageUploader({ file, onChange, error }: ImageUploaderProps) {
  const previewUrl = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  return (
    <div className="space-y-3 rounded-3xl border border-dashed border-slate-300 bg-slate-50 p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-900">Report photo</p>
          <p className="text-xs text-slate-500">JPEG, PNG, or WEBP</p>
        </div>
        {file ? (
          <button type="button" onClick={() => onChange(null)} className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100">
            Remove
          </button>
        ) : null}
      </div>

      <label className="flex min-h-32 cursor-pointer items-center justify-center rounded-2xl border border-slate-200 bg-white px-4 py-6 text-center transition hover:border-[#1f6fb2] hover:bg-[#f4f9fe]">
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="sr-only"
          onChange={(event) => onChange(event.target.files?.[0] || null)}
        />
        <span className="text-sm text-slate-600">
          {file ? file.name : "Drag an image here or click to choose one"}
        </span>
      </label>

      {previewUrl ? (
        <img src={previewUrl} alt="Report preview" className="h-56 w-full rounded-2xl object-cover shadow-sm" />
      ) : null}

      {error ? <p className="text-sm text-rose-700">{error}</p> : null}
    </div>
  );
}

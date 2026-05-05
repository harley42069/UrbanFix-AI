"use client";

import { ChangeEvent, useRef, useState } from "react";

type FileUploadProps = {
  onFileChange: (file: File | null) => void;
  previewUrl: string | null;
  error?: string | null;
};

export default function FileUpload({ onFileChange, previewUrl, error }: FileUploadProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const galleryInputRef = useRef<HTMLInputElement | null>(null);
  const cameraInputRef = useRef<HTMLInputElement | null>(null);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] || null;
    onFileChange(file);
    setIsMenuOpen(false);
  }

  return (
    <div className="space-y-3">
      <div className="relative inline-block">
        <button
          type="button"
          onClick={() => setIsMenuOpen((state) => !state)}
          className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-slate-300 bg-white text-xl font-semibold text-slate-700 transition hover:border-cyan-400 hover:text-cyan-700"
          aria-label="Add image"
        >
          +
        </button>

        {isMenuOpen ? (
          <div className="absolute left-0 top-12 z-10 min-w-44 rounded-xl border border-slate-200 bg-white p-2 shadow-lg">
            <button
              type="button"
              onClick={() => galleryInputRef.current?.click()}
              className="block w-full rounded-lg px-3 py-2 text-left text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              Open gallery
            </button>
            <button
              type="button"
              onClick={() => cameraInputRef.current?.click()}
              className="block w-full rounded-lg px-3 py-2 text-left text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              Take a photo
            </button>
          </div>
        ) : null}
      </div>

      <input
        ref={galleryInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        onChange={handleFileChange}
        className="hidden"
      />
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        onChange={handleFileChange}
        className="hidden"
      />

      {previewUrl ? (
        <button
          type="button"
          onClick={() => onFileChange(null)}
          className="ml-2 rounded-md border border-slate-300 px-3 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100"
        >
          Remove image
        </button>
      ) : null}

      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      {previewUrl ? (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <img src={previewUrl} alt="Preview" className="h-56 w-full object-cover sm:h-72" />
        </div>
      ) : null}
    </div>
  );
}

type AudioPlayerProps = {
  src?: string | null;
  title?: string;
};

export default function AudioPlayer({ src, title = "Audio" }: AudioPlayerProps) {
  if (!src) {
    return null;
  }

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="mb-3 text-sm font-semibold text-slate-900">{title}</p>
      <audio controls className="w-full">
        <source src={src} />
      </audio>
    </div>
  );
}

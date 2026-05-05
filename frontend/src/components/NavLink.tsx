"use client";

export default function NavLink() {
  const handleScroll = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
  };

  return (
    <a
      href="#footer"
      className="rounded-full px-4 py-2 hover:bg-slate-100"
      onClick={handleScroll}
    >
      About
    </a>
  );
}

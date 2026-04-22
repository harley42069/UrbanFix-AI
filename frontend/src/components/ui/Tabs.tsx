"use client";

import { useMemo, useState } from "react";
import type { ReactNode } from "react";

type TabItem = {
  id: string;
  label: string;
  content: ReactNode;
};

type TabsProps = {
  items: TabItem[];
  defaultTabId?: string;
};

export default function Tabs({ items, defaultTabId }: TabsProps) {
  const firstId = items[0]?.id ?? "";
  const [activeId, setActiveId] = useState<string>(defaultTabId || firstId);

  const activeItem = useMemo(() => items.find((item) => item.id === activeId) || items[0], [activeId, items]);

  if (!items.length) {
    return null;
  }

  return (
    <div className="space-y-4">
      <div className="hidden gap-2 border-b border-slate-200 pb-2 md:flex" role="tablist" aria-label="Result tabs">
        {items.map((item) => {
          const selected = item.id === activeId;
          return (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={selected}
              className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
                selected
                  ? "bg-cyan-100 text-cyan-900"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
              onClick={() => setActiveId(item.id)}
            >
              {item.label}
            </button>
          );
        })}
      </div>

      <div className="hidden md:block" role="tabpanel">
        {activeItem?.content}
      </div>

      <div className="md:hidden">
        {items.map((item) => (
          <details
            key={item.id}
            open={item.id === activeId}
            className="mb-2 overflow-hidden rounded-xl border border-slate-200 bg-white"
            onToggle={(event) => {
              const target = event.currentTarget;
              if (target.open) setActiveId(item.id);
            }}
          >
            <summary className="cursor-pointer list-none px-4 py-3 text-sm font-semibold text-slate-800">
              {item.label}
            </summary>
            <div className="border-t border-slate-100 px-4 py-4">{item.content}</div>
          </details>
        ))}
      </div>
    </div>
  );
}

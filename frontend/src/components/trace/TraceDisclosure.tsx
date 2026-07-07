"use client";

import { ChevronDown, type LucideIcon } from "lucide-react";
import { useRef, useState, type ReactNode } from "react";

type TraceDisclosureProps = {
  title: string;
  description?: string;
  icon: LucideIcon;
  accentClassName: string;
  className: string;
  children: ReactNode;
  defaultOpen?: boolean;
  trailing?: ReactNode;
};

export function TraceDisclosure({
  title,
  description,
  icon: Icon,
  accentClassName,
  className,
  children,
  defaultOpen = false,
  trailing,
}: TraceDisclosureProps) {
  const [open, setOpen] = useState(defaultOpen);
  const containerRef = useRef<HTMLDivElement | null>(null);

  function toggleOpen() {
    setOpen((current) => {
      const next = !current;
      if (!current) {
        requestAnimationFrame(() => {
          containerRef.current?.scrollIntoView({
            behavior: "smooth",
            block: "nearest",
          });
        });
      }
      return next;
    });
  }

  return (
    <div className={className} ref={containerRef}>
      <button
        className="flex w-full items-start justify-between gap-3 text-left"
        onClick={toggleOpen}
        type="button"
      >
        <div className="min-w-0">
          <div className={`flex items-center gap-2 text-sm font-medium ${accentClassName}`}>
            <Icon size={16} />
            {title}
          </div>
          {description ? (
            <p className="mt-2 text-sm leading-6 text-[var(--color-ink-soft)]">{description}</p>
          ) : null}
        </div>
        <div className="mt-1 flex shrink-0 items-center gap-2">
          {trailing}
          <ChevronDown
            className={`text-[var(--color-ink-soft)] transition-transform ${open ? "rotate-180" : ""}`}
            size={14}
          />
        </div>
      </button>

      {open ? <div className="mt-3">{children}</div> : null}
    </div>
  );
}

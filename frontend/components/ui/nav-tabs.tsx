"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import {
  CalendarDays,
  Heart,
  Briefcase,
  Users,
  Lightbulb,
} from "lucide-react";

const TABS = [
  { href: "/semaine", label: "Semaine", icon: CalendarDays },
  { href: "/sante", label: "Santé", icon: Heart },
  { href: "/travail", label: "Travail", icon: Briefcase },
  { href: "/social", label: "Social", icon: Users },
  { href: "/idees", label: "Idées", icon: Lightbulb },
] as const;

export function NavTabs() {
  const pathname = usePathname();

  return (
    <nav aria-label="Navigation principale" data-section="navigation" className="flex gap-1 rounded-xl bg-surface-0 p-1">
      {TABS.map(({ href, label, icon: Icon }) => {
        const active = pathname === href || (href === "/semaine" && pathname === "/");
        return (
          <Link
            key={href}
            href={href}
            aria-label={`Aller à ${label}`}
            aria-current={active ? "page" : undefined}
            data-nav={label.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "")}
            className={clsx(
              "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-200",
              active
                ? "bg-accent-blue/20 text-accent-blue shadow-sm"
                : "text-text-muted hover:bg-surface-1 hover:text-text-secondary",
            )}
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
            <span className="hidden sm:inline">{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

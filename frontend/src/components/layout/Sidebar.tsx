"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: "📊" },
  { href: "/analytics", label: "Analytics", icon: "📈" },
  { href: "/service-records", label: "Service Records", icon: "📋" },
  { href: "/machines", label: "Compressors", icon: "⚙️" },
  { href: "/work-orders", label: "Work orders", icon: "📌" },
  { href: "/my-work", label: "My work", icon: "🛠️" },
  { href: "/notifications", label: "Notifications", icon: "🔔" },
  { href: "/workflow", label: "Workflows", icon: "🔧" },
  { href: "/configuration", label: "Configuration", icon: "👥" },
  { href: "/upload", label: "Upload Data", icon: "📤" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-slate-800 text-white flex flex-col shrink-0">
      <div className="px-6 py-5 border-b border-slate-700">
        <h1 className="text-xl font-bold tracking-tight">
          <span className="text-amber-400">Compressor</span>IQ
        </h1>
        <p className="text-xs text-slate-400 mt-1">Predictive Maintenance</p>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`sidebar-link ${isActive ? "active" : "text-slate-300"}`}
            >
              <span className="text-lg">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
        <div className="pt-3 mt-2 border-t border-slate-700 space-y-1">
          <Link
            href="/user-manual"
            className={`sidebar-link ${pathname === "/user-manual" ? "active" : "text-slate-300"}`}
          >
            <span className="text-lg" aria-hidden>
              📘
            </span>
            User manual
          </Link>
          <a
            href="/CompressorIQ_User_Manual.pdf"
            target="_blank"
            rel="noopener noreferrer"
            className="sidebar-link text-slate-300 hover:text-amber-200"
          >
            <span className="text-lg" aria-hidden>
              📕
            </span>
            Manual PDF (text + screens)
          </a>
          <a
            href="/CompressorIQ_User_Guide_Screenshots.pdf"
            target="_blank"
            rel="noopener noreferrer"
            className="sidebar-link text-slate-300 hover:text-amber-200"
          >
            <span className="text-lg" aria-hidden>
              🖼️
            </span>
            Screenshots PDF
          </a>
        </div>
      </nav>

      <div className="px-4 py-4 border-t border-slate-700">
        <div className="text-xs text-slate-500">CompressorIQ v0.1.0</div>
        <div className="text-xs text-slate-500">MVP – Field Service</div>
      </div>
    </aside>
  );
}

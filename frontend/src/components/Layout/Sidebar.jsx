import { NavLink } from "react-router-dom";
import {
  Files,
  Search,
  Upload,
  Tag,
  Users,
  ScrollText,
  LayoutDashboard,
  BrainCircuit,
} from "lucide-react";
import clsx from "clsx";
import { useAuth } from "../../context/AuthContext";
import ThemeToggle from "../UI/ThemeToggle";

const NAV_ALL = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/documents", label: "Documentos", icon: Files },
  { to: "/search", label: "Búsqueda", icon: Search },
];
const NAV_EDITOR = [{ to: "/upload", label: "Subir archivo", icon: Upload }];
const NAV_ADMIN = [
  { to: "/categories", label: "Categorías", icon: Tag },
  { to: "/users", label: "Usuarios", icon: Users },
  { to: "/audit", label: "Auditoría", icon: ScrollText },
];

function NavItem({ to, label, icon: Icon, open }) {
  return (
    <NavLink
      to={to}
      title={!open ? label : undefined}
      className={({ isActive }) =>
        clsx(
          "nav-indicator relative flex items-center py-2.5 rounded-[var(--radius-md)] text-sm",
          "transition-all duration-200 ease-out",
          open ? "gap-3 px-3" : "justify-center px-0",
          isActive
            ? "active bg-[var(--color-primary-subtle)] text-[var(--color-primary)] font-medium"
            : [
                "text-[var(--color-text-secondary)]",
                "hover:bg-[var(--color-bg-surface-2)]",
                "hover:text-[var(--color-text-primary)]",
                "hover:translate-x-0.5",
              ],
        )
      }
    >
      {({ isActive }) => (
        <>
          <Icon
            size={16}
            className={clsx(
              "shrink-0 transition-all duration-200",
              isActive
                ? "text-[var(--color-primary)]"
                : "text-[var(--color-text-secondary)]",
            )}
          />
          {open && <span className="truncate">{label}</span>}
        </>
      )}
    </NavLink>
  );
}

function SectionLabel({ children }) {
  return (
    <p className="px-3 pt-4 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.10em] text-[var(--color-text-muted)]">
      {children}
    </p>
  );
}

function Divider() {
  return (
    <div
      className="my-2 mx-2 h-px"
      style={{ background: "var(--color-border)" }}
    />
  );
}

/**
 * Sidebar de navegación.
 * - Desktop (lg+): inline, w-60 cuando open, w-14 (icon-only) cuando cerrado.
 * - Mobile (<lg): fixed overlay w-60, se monta/desmonta desde Layout.
 *
 * @param {{ open: boolean, mobile: boolean }} props
 */
export default function Sidebar({ open, mobile = false }) {
  const { isAdmin, isEditor } = useAuth();

  return (
    <aside
      className={clsx(
        "h-screen flex flex-col shrink-0",
        "transition-[width,transform] duration-200 ease-in-out",
        mobile
          ? // Móvil: siempre fixed, siempre w-60, sin modo icon-only
            "fixed inset-y-0 left-0 z-30 w-60 max-w-[75vw]"
          : // Desktop: inline, cambia de ancho según open
            clsx("relative", open ? "w-60" : "w-14"),
      )}
      style={{
        backgroundColor: "var(--color-bg-page)",
        borderRight: "1px solid var(--color-border)",
      }}
    >
      {/* ── Logo ── */}
      <div
        className={clsx(
          "flex items-center h-14 shrink-0",
          open || mobile ? "px-4 gap-2.5" : "justify-center px-0",
        )}
      >
        <div
          className="w-7 h-7 rounded-[var(--radius-md)] flex items-center justify-center shrink-0 transition-transform duration-200 hover:scale-110"
          style={{ backgroundColor: "var(--color-primary)" }}
        >
          <BrainCircuit size={14} className="text-white" />
        </div>
        {(open || mobile) && (
          <span
            className="text-sm font-semibold truncate"
            style={{ color: "var(--color-text-primary)" }}
          >
            DocMind IA
          </span>
        )}
      </div>

      {/* Separador */}
      <div
        className="mx-4 h-px shrink-0"
        style={{
          background:
            "linear-gradient(to right, transparent, var(--color-border), transparent)",
        }}
      />

      {/* ── Navegación ── */}
      <nav
        className={clsx(
          "flex-1 overflow-y-auto py-3 flex flex-col gap-0.5",
          open || mobile ? "px-3" : "px-2",
        )}
      >
        {NAV_ALL.map((item) => (
          <NavItem key={item.to} {...item} open={open || mobile} />
        ))}

        {isEditor && (
          <>
            {open || mobile ? (
              <SectionLabel>Contenido</SectionLabel>
            ) : (
              <Divider />
            )}
            {NAV_EDITOR.map((item) => (
              <NavItem key={item.to} {...item} open={open || mobile} />
            ))}
          </>
        )}

        {isAdmin && (
          <>
            {open || mobile ? (
              <SectionLabel>Administración</SectionLabel>
            ) : (
              <Divider />
            )}
            {NAV_ADMIN.map((item) => (
              <NavItem key={item.to} {...item} open={open || mobile} />
            ))}
          </>
        )}
      </nav>

      {/* Separador footer */}
      <div
        className="mx-4 h-px shrink-0"
        style={{
          background:
            "linear-gradient(to right, transparent, var(--color-border), transparent)",
        }}
      />

      {/* ── Footer ── */}
      <div
        className={clsx(
          "py-3 shrink-0 flex items-center",
          open || mobile ? "px-3 justify-between" : "justify-center px-0",
        )}
      >
        <ThemeToggle />
        {(open || mobile) && (
          <span
            className="text-[10px]"
            style={{ color: "var(--color-text-muted)" }}
          >
            UNAP · 2026
          </span>
        )}
      </div>
    </aside>
  );
}

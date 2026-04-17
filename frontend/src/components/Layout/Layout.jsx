import { useState, useEffect, useCallback } from "react";
import Sidebar from "./Sidebar";
import TopBar from "./TopBar";

export default function Layout({ title, children }) {
  const isMobile = () =>
    typeof window !== "undefined" && window.innerWidth < 1024;

  const [sidebarOpen, setSidebarOpen] = useState(() => !isMobile());

  const toggle = useCallback(() => setSidebarOpen((v) => !v), []);

  useEffect(() => {
    const onResize = () => {
      if (window.innerWidth >= 1024) {
        setSidebarOpen(true);
      } else {
        setSidebarOpen(false);
      }
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const mobile = isMobile();

  return (
    <div
      className="flex h-screen overflow-hidden"
      style={{ backgroundColor: "var(--color-bg-page)" }}
    >
      {/* Backdrop — solo móvil cuando sidebar abierto */}
      {sidebarOpen && mobile && (
        <div
          className="fixed inset-0 z-20 backdrop-blur-sm lg:hidden"
          style={{ backgroundColor: "rgba(0,0,0,0.50)" }}
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* En móvil: sidebar solo existe en el DOM cuando está abierto */}
      {/* En desktop: sidebar siempre presente, cambia de ancho */}
      {(!mobile || sidebarOpen) && (
        <Sidebar open={sidebarOpen} mobile={mobile} />
      )}

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopBar title={title} onToggleSidebar={toggle} />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}

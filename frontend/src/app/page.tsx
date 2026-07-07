"use client";

import { ChatPanel } from "@/components/chat/ChatPanel";
import { InspectorPanel } from "@/components/editor/InspectorPanel";
import { Navbar } from "@/components/layout/Navbar";
import { ResizeHandle } from "@/components/layout/ResizeHandle";
import { Sidebar } from "@/components/layout/Sidebar";
import { AppProvider, useAppStore } from "@/lib/store";

function Workspace() {
  const {
    sidebarWidth,
    inspectorWidth,
    inspectorOpen,
    setSidebarWidth,
    setInspectorWidth
  } = useAppStore();

  return (
    <main className="h-screen overflow-hidden p-4 md:p-6">
      <div className="mx-auto flex h-full max-w-[1800px] flex-col gap-4">
        <Navbar />
        <div className="flex min-h-0 flex-1 gap-0 overflow-hidden">
          <div className="min-h-0" style={{ width: sidebarWidth }}>
            <Sidebar />
          </div>
          <ResizeHandle onResize={(delta) => setSidebarWidth(Math.max(260, sidebarWidth + delta))} />
          <ChatPanel />
          {inspectorOpen ? (
            <>
              <ResizeHandle
                onResize={(delta) => setInspectorWidth(Math.max(320, inspectorWidth - delta))}
              />
              <div className="min-h-0" style={{ width: inspectorWidth }}>
                <InspectorPanel />
              </div>
            </>
          ) : null}
        </div>
      </div>
    </main>
  );
}

export default function Page() {
  return (
    <AppProvider>
      <Workspace />
    </AppProvider>
  );
}

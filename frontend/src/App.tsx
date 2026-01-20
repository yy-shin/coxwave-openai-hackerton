import clsx from "clsx";
import { useRef } from "react";

import { ChatKitPanel } from "./components/ChatKitPanel";
import type { ChatKit } from "./components/ChatKitPanel";
import { FinalVideoPanel } from "./components/FinalVideoPanel";
import { StoryboardPanel } from "./components/StoryboardPanel";
import { ClipSelectionPanel } from "./components/ClipSelectionPanel";
import { ThemeToggle } from "./components/ThemeToggle";
import { LanguageToggle } from "./components/LanguageToggle";
import { useAppStore } from "./store/useAppStore";
import { t } from "./lib/i18n";

export default function App() {
  const chatkitRef = useRef<ChatKit | null>(null);

  const scheme = useAppStore((state) => state.scheme);
  const language = useAppStore((state) => state.language);
  const rightPanel = useAppStore((state) => state.rightPanel);
  const i18n = t(language);

  const containerClass = clsx(
    "h-full bg-gradient-to-br transition-colors duration-300",
    scheme === "dark"
      ? "from-slate-900 via-slate-950 to-slate-850 text-slate-100"
      : "from-slate-100 via-white to-slate-200 text-slate-900",
  );
  const headerBarClass = clsx(
    "sticky top-0 z-30 w-full border-b backdrop-blur",
    scheme === "dark"
      ? "bg-slate-950/80 border-slate-800/70 text-slate-100"
      : "bg-white/90 border-slate-200/70 text-slate-900",
  );

  return (
    <div className={containerClass}>
      <div className={headerBarClass}>
        <div className="relative mx-auto flex w-full max-w-7xl items-center gap-3 px-4 py-3 sm:gap-4 sm:px-6 sm:py-4">
          <h1 className="flex items-center gap-4 text-base font-semibold tracking-wide sm:text-lg">
            <img src="/favicon.png" alt="OvenAI" className="h-[24px] w-7 sm:h-[26px] sm:w-8" />
            <span className="translate-y-[1px]">OvenAI</span>
          </h1>
          <p className="hidden flex-1 translate-y-[1px] text-sm text-slate-600 sm:block dark:text-slate-300">
            {i18n.tagline}
          </p>
          <div className="ml-auto flex items-center gap-2">
            <LanguageToggle />
            <ThemeToggle />
          </div>
        </div>
      </div>
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-4 pb-6 pt-4 sm:px-6 lg:flex-row lg:gap-6 lg:pb-10 lg:pt-6">
        <ChatKitPanel
          className="relative h-[60vh] w-full shrink-0 overflow-hidden rounded-2xl bg-white/80 shadow-lg ring-1 ring-slate-200/60 backdrop-blur sm:rounded-3xl lg:h-[calc(100vh-140px)] lg:w-[380px] xl:w-[420px] dark:bg-slate-900/70 dark:ring-slate-800/60"
          onChatKitReady={(chatkit) => (chatkitRef.current = chatkit)}
        />
        {rightPanel === "storyboard" && (
          <StoryboardPanel
            className="relative min-h-[400px] w-full flex-1 overflow-hidden rounded-2xl bg-white/80 shadow-lg ring-1 ring-slate-200/60 backdrop-blur sm:rounded-3xl lg:h-[calc(100vh-140px)] lg:min-h-0 dark:bg-slate-900/70 dark:ring-slate-800/60"
          />
        )}
        {rightPanel === "video" && (
          <ClipSelectionPanel
            className="relative min-h-[400px] w-full flex-1 overflow-hidden rounded-2xl bg-white/80 shadow-lg ring-1 ring-slate-200/60 backdrop-blur sm:rounded-3xl lg:h-[calc(100vh-140px)] lg:min-h-0 dark:bg-slate-900/70 dark:ring-slate-800/60"
          />
        )}
        {rightPanel === "final" && (
          <FinalVideoPanel
            className="relative min-h-[400px] w-full flex-1 overflow-hidden rounded-2xl bg-white/80 shadow-lg ring-1 ring-slate-200/60 backdrop-blur sm:rounded-3xl lg:h-[calc(100vh-140px)] lg:min-h-0 dark:bg-slate-900/70 dark:ring-slate-800/60"
          />
        )}
      </div>
    </div>
  );
}

import { create } from "zustand";

import { CAT_STATE_API_URL, THEME_STORAGE_KEY, LANG_STORAGE_KEY } from "../lib/config";
import type { CatSpeechPayload, CatStatePayload } from "../lib/cat";
import { DEFAULT_CAT_STATE } from "../lib/cat";
import type { Language } from "../lib/i18n";
import confetti from "canvas-confetti";

export type ColorScheme = "light" | "dark";
export type RightPanelType = "storyboard" | "video" | "final";

type SpeechState = (CatSpeechPayload & { id: number }) | null;

export type VideoCandidate = {
  id: string;
  clipIndex: number;
  url: string;
  thumbnailUrl?: string;
  model: string;
  status: "pending" | "generating" | "completed" | "failed";
};

export type ImageInput = {
  url?: string;
  base64?: string;
  mime_type?: "image/jpeg" | "image/png" | "image/webp";
};

export type BaseClip = {
  scene_description: string;
  prompt: string;
  duration: number;
  input_image?: ImageInput;
};

export type SoraClip = BaseClip & {
  provider: "sora";
  model?: "sora-2" | "sora-2-pro";
};

export type VeoClip = BaseClip & {
  provider: "veo";
  model?: "veo-3.1-generate-001" | "veo-3.1-fast-generate-001" | "veo-3.1-generate-preview" | "veo-3.1-fast-generate-preview";
  negative_prompt?: string;
  last_frame?: ImageInput;
  reference_images?: ImageInput[];
  num_outputs?: number;
};

export type Clip = SoraClip | VeoClip;

export type Storyboard = {
  description: string;
  total_duration: number;
  clips: Clip[];
} | null;

type AppState = {
  scheme: ColorScheme;
  setScheme: (scheme: ColorScheme) => void;
  language: Language;
  setLanguage: (language: Language) => void;
  threadId: string | null;
  setThreadId: (threadId: string | null) => void;
  cat: CatStatePayload;
  refreshCat: (overrideId?: string | null) => Promise<CatStatePayload | undefined>;
  applyCatUpdate: (update: Partial<CatStatePayload>) => void;
  speech: SpeechState;
  setSpeech: (payload: CatSpeechPayload) => void;
  flashMessage: string | null;
  setFlashMessage: (message: string | null) => void;
  rightPanel: RightPanelType;
  setRightPanel: (panel: RightPanelType) => void;
  videoCandidates: VideoCandidate[];
  setVideoCandidates: (candidates: VideoCandidate[]) => void;
  selectedVideoIds: Record<number, string>;
  selectVideo: (clipIndex: number, videoId: string) => void;
  storyboard: Storyboard;
  originalStoryboard: Storyboard;
  setStoryboard: (storyboard: Storyboard) => void;
  updateStoryboardDescription: (description: string) => void;
  updateClip: (clipIndex: number, updates: Partial<Clip>) => void;
  isGeneratingVideos: boolean;
  setIsGeneratingVideos: (isGenerating: boolean) => void;
};

const SPEECH_TIMEOUT_MS = 10_000;
const FLASH_TIMEOUT_MS = 10_000;

let speechTimer: ReturnType<typeof setTimeout> | null = null;
let flashTimer: ReturnType<typeof setTimeout> | null = null;

function clearSpeechTimer() {
  if (speechTimer) {
    clearTimeout(speechTimer);
    speechTimer = null;
  }
}

function clearFlashTimer() {
  if (flashTimer) {
    clearTimeout(flashTimer);
    flashTimer = null;
  }
}

function getInitialScheme(): ColorScheme {
  if (typeof window === "undefined") {
    return "light";
  }
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY) as ColorScheme | null;
  if (stored === "light" || stored === "dark") {
    return stored;
  }
  return "light";
}

function getInitialLanguage(): Language {
  if (typeof window === "undefined") {
    return "ko";
  }
  const stored = window.localStorage.getItem(LANG_STORAGE_KEY) as Language | null;
  if (stored === "ko" || stored === "en") {
    return stored;
  }
  return "ko";
}

function syncLanguageWithStorage(language: Language) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(LANG_STORAGE_KEY, language);
}

function syncSchemeWithDocument(scheme: ColorScheme) {
  if (typeof document === "undefined" || typeof window === "undefined") {
    return;
  }
  const root = document.documentElement;
  if (scheme === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
  window.localStorage.setItem(THEME_STORAGE_KEY, scheme);
}

function celebrateReveal() {
  confetti({
    particleCount: 50,
    spread: 100,
    origin: { y: 0.7 },
    zIndex: 1000,
    scalar: 0.9,
  });
}

export const useAppStore = create<AppState>((set, get) => {
  const initialScheme = getInitialScheme();
  const initialLanguage = getInitialLanguage();
  syncSchemeWithDocument(initialScheme);

  return {
    scheme: initialScheme,
    setScheme: (scheme) => {
      syncSchemeWithDocument(scheme);
      set({ scheme });
    },
    language: initialLanguage,
    setLanguage: (language) => {
      syncLanguageWithStorage(language);
      set({ language });
    },
    threadId: null,
    setThreadId: (threadId) => {
      const previousId = get().threadId;
      if (previousId === threadId) {
        return;
      }
      clearSpeechTimer();
      clearFlashTimer();
      set({ threadId, speech: null, flashMessage: null });
      void get().refreshCat(threadId ?? null);
    },
    cat: DEFAULT_CAT_STATE,
    applyCatUpdate: (update) => {
      const prev = get().cat
      if (prev.name === "Unnamed Cat" && update.name !== prev.name) {
        celebrateReveal();
      }

      if (
        (prev.energy < 10 || prev.happiness < 10 || prev.cleanliness < 10) &&
        (update.energy === 10 && update.happiness === 10 && update.cleanliness === 10)) {
        const heart = confetti.shapeFromText({ text: '❤️', scalar: 2 });
        confetti({
          scalar: 2,
          particleCount: 10,
          flat: true,
          gravity: 0.5,
          spread: 120,
          origin: { y: 0.7 },
          zIndex: 1000,
          shapes: [heart],
        });
      }

      set((state) => ({
        cat: {
          ...state.cat,
          ...update,
          updatedAt: update.updatedAt ?? new Date().toISOString(),
        },
      }));
    },
    refreshCat: async (overrideId) => {
      const id = overrideId ?? get().threadId;
      if (!id) {
        set({
          cat: {
            ...DEFAULT_CAT_STATE,
            threadId: null,
            updatedAt: new Date().toISOString(),
          },
        });
        return;
      }
      try {
        const response = await fetch(`${CAT_STATE_API_URL}/${encodeURIComponent(id)}`);
        if (!response.ok) {
          throw new Error(`Failed to load cat state (${response.status})`);
        }
        const data = (await response.json()) as { cat?: CatStatePayload };
        if (data?.cat) {
          const prev = get().cat
          if (prev.name === "Unnamed Cat" && data.cat.name !== prev.name) {
            celebrateReveal();
          }

          set({ cat: data.cat });
          return data.cat;
        }
      } catch (error) {
        console.error("Failed to fetch cat state", error);
      }
    },
    speech: null,
    setSpeech: (payload) => {
      const speechPayload: SpeechState =
        payload ? { ...payload, id: Date.now() } : null;

      clearSpeechTimer();
      clearFlashTimer();
      set({ speech: speechPayload, flashMessage: null });

      if (!speechPayload) {
        return;
      }

      speechTimer = setTimeout(() => {
        set({ speech: null });
        speechTimer = null;
      }, SPEECH_TIMEOUT_MS);
    },
    flashMessage: null,
    setFlashMessage: (message) => {
      if (!message) {
        clearFlashTimer();
        set({ flashMessage: null });
        return;
      }

      clearFlashTimer();
      clearSpeechTimer();
      set({ flashMessage: message, speech: null });

      flashTimer = setTimeout(() => {
        set({ flashMessage: null });
        flashTimer = null;
      }, FLASH_TIMEOUT_MS);
    },
    rightPanel: "storyboard",
    setRightPanel: (panel) => set({ rightPanel: panel }),
    videoCandidates: [],
    setVideoCandidates: (candidates) => set({ videoCandidates: candidates }),
    selectedVideoIds: {},
    selectVideo: (sceneId, videoId) =>
      set((state) => ({
        selectedVideoIds: { ...state.selectedVideoIds, [sceneId]: videoId },
      })),
    // TODO: 실제 연동 시 null로 복구
    storyboard: {
      description: "A high-energy game marketing video showcasing Cookie Run character transformation. Appeals to casual mobile gamers aged 18-35 through vibrant colors, dynamic action sequences, and character progression fantasy. Style: 2D animated with cel-shading effects.",
      total_duration: 24,
      clips: [
        {
          scene_description: "Opening shot: Cookie character appears in a magical forest",
          provider: "veo",
          prompt: "A cute 2D animated cookie character with big eyes stands in a colorful magical forest, sunlight filtering through trees, whimsical atmosphere, smooth animation, vibrant colors",
          duration: 8,
          negative_prompt: "blurry, low quality, distorted, realistic",
          reference_images: [{ url: "https://example.com/cookie_character.png" }],
        },
        {
          scene_description: "Transformation: Cookie gains superpowers with glowing effects",
          provider: "veo",
          prompt: "The cookie character begins glowing with golden energy, magical transformation sequence, swirling particles, dynamic camera movement, epic power-up moment, 2D animated style",
          duration: 8,
          negative_prompt: "blurry, distorted",
          input_image: { url: "https://example.com/transformation_start.png" },
        },
        {
          scene_description: "Finale: Superhero cookie in action pose with logo reveal",
          provider: "sora",
          prompt: "Superhero cookie character in heroic pose, cape flowing, magical energy surrounding them, camera pulls back to reveal Cookie Run logo, celebratory particle effects, 2D animated style",
          duration: 8,
        },
      ],
    },
    originalStoryboard: {
      description: "A high-energy game marketing video showcasing Cookie Run character transformation. Appeals to casual mobile gamers aged 18-35 through vibrant colors, dynamic action sequences, and character progression fantasy. Style: 2D animated with cel-shading effects.",
      total_duration: 24,
      clips: [
        {
          scene_description: "Opening shot: Cookie character appears in a magical forest",
          provider: "veo",
          prompt: "A cute 2D animated cookie character with big eyes stands in a colorful magical forest, sunlight filtering through trees, whimsical atmosphere, smooth animation, vibrant colors",
          duration: 8,
          negative_prompt: "blurry, low quality, distorted, realistic",
          reference_images: [{ url: "https://example.com/cookie_character.png" }],
        },
        {
          scene_description: "Transformation: Cookie gains superpowers with glowing effects",
          provider: "veo",
          prompt: "The cookie character begins glowing with golden energy, magical transformation sequence, swirling particles, dynamic camera movement, epic power-up moment, 2D animated style",
          duration: 8,
          negative_prompt: "blurry, distorted",
          input_image: { url: "https://example.com/transformation_start.png" },
        },
        {
          scene_description: "Finale: Superhero cookie in action pose with logo reveal",
          provider: "sora",
          prompt: "Superhero cookie character in heroic pose, cape flowing, magical energy surrounding them, camera pulls back to reveal Cookie Run logo, celebratory particle effects, 2D animated style",
          duration: 8,
        },
      ],
    },
    setStoryboard: (storyboard) => set({ storyboard, originalStoryboard: storyboard }),
    updateStoryboardDescription: (description) =>
      set((state) => {
        if (!state.storyboard) return state;
        return {
          storyboard: { ...state.storyboard, description },
        };
      }),
    updateClip: (clipIndex, updates) =>
      set((state) => {
        if (!state.storyboard) return state;
        const newClips = [...state.storyboard.clips];
        newClips[clipIndex] = { ...newClips[clipIndex], ...updates } as Clip;
        return {
          storyboard: { ...state.storyboard, clips: newClips },
        };
      }),
    isGeneratingVideos: false,
    setIsGeneratingVideos: (isGenerating) => set({ isGeneratingVideos: isGenerating }),
  };
});

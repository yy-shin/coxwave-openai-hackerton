// ============================================
// Theme & UI Types
// ============================================
export type ColorScheme = "light" | "dark";
export type RightPanelType = "storyboard" | "video" | "final";

// ============================================
// Storyboard & Video Types
// ============================================
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
  model?:
    | "veo-3.1-generate-001"
    | "veo-3.1-fast-generate-001"
    | "veo-3.1-generate-preview"
    | "veo-3.1-fast-generate-preview";
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
};

export type VideoStatus = "pending" | "generating" | "completed" | "failed";

export type VideoCandidate = {
  id: string;
  clipIndex: number;
  url: string;
  thumbnailUrl?: string;
  model: string;
  status: VideoStatus;
};

// ============================================
// Cat Types (for Cat Lounge feature)
// ============================================
export type CatColorPattern =
  | "orange_tabby"
  | "gray_tabby"
  | "calico"
  | "tuxedo"
  | "siamese"
  | "void";

export type CatSpeechPayload = {
  text: string;
  mood?: "happy" | "neutral" | "sleepy";
};

export type CatStatePayload = {
  threadId: string | null;
  name: string;
  colorPattern: CatColorPattern;
  energy: number;
  happiness: number;
  cleanliness: number;
  traits: string[];
  backstory: string;
  updatedAt: string;
};

export const DEFAULT_CAT_STATE: CatStatePayload = {
  threadId: null,
  name: "Unnamed Cat",
  colorPattern: "orange_tabby",
  energy: 10,
  happiness: 10,
  cleanliness: 10,
  traits: [],
  backstory: "",
  updatedAt: new Date().toISOString(),
};

// ============================================
// i18n Types (re-exported from lib/i18n)
// ============================================
export type { Language, Translations } from "../lib/i18n";

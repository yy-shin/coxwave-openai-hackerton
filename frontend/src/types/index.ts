// ============================================
// Theme & UI Types
// ============================================
export type ColorScheme = "light" | "dark";
export type RightPanelType = "storyboard" | "video" | "final";

// ============================================
// Storyboard & Video Types
// ============================================
export type ImageInput = {
  filePath: string;
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
// Backend Project State Types (from update_project_status)
// ============================================

export type BackendImageInput = {
  filePath: string;
};

export type BackendGenerationInput = {
  provider: "veo" | "sora";
  prompt: string;
  negativePrompt: string | null;
  referenceImages: BackendImageInput[] | null;
  inputImage: BackendImageInput | null;
};

export type BackendSegment = {
  sceneDescription: string;
  duration: number;
  generationInputs: BackendGenerationInput[];
  selectedVideoUrl: string | null;
  videoVariants: string[];
  selectedVariantIndex: number | null;
};

export type BackendStoryboard = {
  segments: BackendSegment[];
};

export type ProjectStatePayload = {
  threadId?: string;
  title: string;
  description: string;
  aspectRatio: string;
  totalDuration: number;
  referenceVideoUrl: string | null;
  referenceImages: BackendImageInput[];
  storyboard: BackendStoryboard;
  storyboardApproved: boolean;
  finalVideoUrl: string | null;
  thumbnailUrl: string | null;
  bannerUrl: string | null;
  marketingCopy: string | null;
  updatedAt: string;
};

// ============================================
// Transformer: Backend -> Frontend
// ============================================

/**
 * Convert backend segment to frontend clip format.
 * Uses the first generationInput as the primary clip configuration.
 */
export function transformSegmentToClip(segment: BackendSegment): Clip {
  // Use the first generationInput as the primary configuration
  const primaryInput = segment.generationInputs[0];

  if (!primaryInput) {
    // Fallback if no generation inputs
    return {
      provider: "veo",
      scene_description: segment.sceneDescription,
      prompt: "",
      duration: segment.duration,
    };
  }

  const baseClip: BaseClip = {
    scene_description: segment.sceneDescription,
    prompt: primaryInput.prompt,
    duration: segment.duration,
    input_image: primaryInput.inputImage
      ? { url: primaryInput.inputImage.url }
      : undefined,
  };

  if (primaryInput.provider === "sora") {
    return {
      ...baseClip,
      provider: "sora",
    } as SoraClip;
  }

  // Default to VeoClip for "veo"
  return {
    ...baseClip,
    provider: "veo",
    negative_prompt: primaryInput.negativePrompt ?? undefined,
    reference_images: primaryInput.referenceImages?.map((img) => ({
      url: img.url,
    })),
  } as VeoClip;
}

/**
 * Convert backend project state to frontend storyboard format.
 */
export function transformProjectStateToStoryboard(
  state: ProjectStatePayload
): Storyboard {
  return {
    description: state.description,
    total_duration: state.totalDuration,
    clips: state.storyboard.segments.map(transformSegmentToClip),
  };
}

// ============================================
// i18n Types (re-exported from lib/i18n)
// ============================================
export type { Language, Translations } from "../lib/i18n";

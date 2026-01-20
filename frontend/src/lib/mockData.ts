import type { Storyboard, VideoCandidate } from "../types";

// Example storyboard for testing
export const EXAMPLE_STORYBOARD: Storyboard = {
  description:
    "A high-energy game marketing video showcasing Cookie Run character transformation. Appeals to casual mobile gamers aged 18-35 through vibrant colors, dynamic action sequences, and character progression fantasy. Style: 2D animated with cel-shading effects.",
  total_duration: 24,
  clips: [
    {
      scene_description: "Opening shot: Cookie character appears in a magical forest",
      provider: "veo",
      prompt:
        "A cute 2D animated cookie character with big eyes stands in a colorful magical forest, sunlight filtering through trees, whimsical atmosphere, smooth animation, vibrant colors",
      duration: 8,
      negative_prompt: "blurry, low quality, distorted, realistic",
      reference_images: [{ url: "https://example.com/cookie_character.png" }],
    },
    {
      scene_description: "Transformation: Cookie gains superpowers with glowing effects",
      provider: "veo",
      prompt:
        "The cookie character begins glowing with golden energy, magical transformation sequence, swirling particles, dynamic camera movement, epic power-up moment, 2D animated style",
      duration: 8,
      negative_prompt: "blurry, distorted",
      input_image: { url: "https://example.com/transformation_start.png" },
    },
    {
      scene_description: "Finale: Superhero cookie in action pose with logo reveal",
      provider: "sora",
      prompt:
        "Superhero cookie character in heroic pose, cape flowing, magical energy surrounding them, camera pulls back to reveal Cookie Run logo, celebratory particle effects, 2D animated style",
      duration: 8,
    },
  ],
};

// Mock clips for VideoGenerationPanel
export const MOCK_CLIPS = [
  { index: 0, scene_description: "Opening shot: Cookie character appears", duration: 8 },
  { index: 1, scene_description: "Transformation: Cookie gains superpowers", duration: 8 },
  { index: 2, scene_description: "Finale: Superhero cookie with logo reveal", duration: 8 },
];

// Mock video candidates for VideoGenerationPanel
export const MOCK_VIDEO_CANDIDATES: VideoCandidate[] = [
  // Clip 0 - 4 candidates
  {
    id: "vid_0_1",
    clipIndex: 0,
    url: "/mock_video/phase1-1.mp4",
    model: "Veo 3",
    status: "completed",
  },
  {
    id: "vid_0_2",
    clipIndex: 0,
    url: "/mock_video/phase1-2.mp4",
    model: "Veo 3",
    status: "completed",
  },
  {
    id: "vid_0_3",
    clipIndex: 0,
    url: "/mock_video/phase1-3.mp4",
    model: "Sora 2",
    status: "completed",
  },
  {
    id: "vid_0_4",
    clipIndex: 0,
    url: "/mock_video/phase1-4.mp4",
    model: "Sora 2",
    status: "completed",
  },
  // Clip 1 - 1 candidate
  {
    id: "vid_1_1",
    clipIndex: 1,
    url: "/mock_video/phase2-1.mp4",
    model: "Veo 3",
    status: "completed",
  },
  // Clip 2 - 2 candidates
  {
    id: "vid_2_1",
    clipIndex: 2,
    url: "/mock_video/phase3-1.mp4",
    model: "Veo 3",
    status: "completed",
  },
  {
    id: "vid_2_2",
    clipIndex: 2,
    url: "/mock_video/phase3-2.mp4",
    model: "Sora 2",
    status: "completed",
  },
];

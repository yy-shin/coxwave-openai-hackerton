export type Language = "ko" | "en";

export const translations = {
  ko: {
    // Header
    tagline: "AI로 비디오 광고를 쉽고 빠르게 만들어보세요.",

    // Storyboard Panel
    storyboard: "스토리보드",
    totalDurationClips: (duration: number, clips: number) =>
      `총 ${duration}초 · ${clips}개 클립`,
    storyboardEmpty: "광고 영상의 컷 구성을 확인하세요",
    generatingVideos: "비디오 생성 중...",
    generatingVideosDesc: "각 클립에 대해 AI 모델로 비디오를 생성하고 있습니다",
    chatPrompt1: "채팅에서 광고 요청을 입력하면",
    chatPrompt2: "스토리보드가 여기에 생성됩니다",
    generating: "생성 중...",
    generate: "생성하기",
    seconds: "초",
    videoDescription: "비디오 설명",
    sceneDescription: "씬 설명",
    prompt: "프롬프트",
    inputImage: "시작 이미지",
    lastFrame: "종료 이미지",
    referenceImages: "참조 이미지",
    noImage: "이미지 없음",
    veoOnly: "Veo 전용",
    optional: "선택",

    // Clip Selection Panel
    clipSelection: "클립 선택",
    videoGenerationDesc: "각 클립별로 생성된 비디오를 확인하고 선택하세요",
    backToStoryboard: "스토리보드로 돌아가기",
    videoNotPlayable: "비디오를 재생할 수 없습니다.",
    generatingWith: (model: string) => `${model}로 생성 중...`,
    noVideosForClip: "이 클립에 생성된 비디오가 없습니다",
    selectVideoPrompt: "아래에서 비디오를 선택하세요",
    generatedVideos: (count: number) => `생성된 비디오 (${count}개)`,
    clipSelectionStatus: (selected: number, total: number) =>
      `${selected} / ${total} 클립 선택 완료`,
    selected: "선택됨",
    createFinalVideo: "최종 비디오 생성",
    creating: "생성 중...",
    creatingFinalVideo: "최종 비디오 생성 중...",
    creatingFinalVideoDesc: "선택한 클립들을 하나의 영상으로 합치고 있습니다",

    // Final Video Panel
    finalVideo: "최종 비디오",
    finalVideoDesc: "완성된 광고 영상을 확인하세요",
    backToSceneSelection: "씬 선택으로 돌아가기",
    videoReady: "비디오 준비 완료",
    pressPlayToWatch: "재생 버튼을 눌러 확인하세요",
    videoComplete: "광고 영상이 완성되었습니다!",
    scenesJoined: "선택한 씬들이 하나의 영상으로 합쳐졌습니다",
    createAgain: "다시 만들기",
    download: "다운로드",
  },
  en: {
    // Header
    tagline: "Create video ads easily and quickly with AI.",

    // Storyboard Panel
    storyboard: "Storyboard",
    totalDurationClips: (duration: number, clips: number) =>
      `${duration}s total · ${clips} clips`,
    storyboardEmpty: "Review the scene composition of your ad video",
    generatingVideos: "Generating videos...",
    generatingVideosDesc: "AI models are generating videos for each clip",
    chatPrompt1: "Enter your ad request in the chat",
    chatPrompt2: "and the storyboard will be generated here",
    generating: "Generating...",
    generate: "Generate",
    seconds: "s",
    videoDescription: "Video Description",
    sceneDescription: "Scene Description",
    prompt: "Prompt",
    inputImage: "Start Image",
    lastFrame: "End Image",
    referenceImages: "Reference Images",
    noImage: "No image",
    veoOnly: "Veo only",
    optional: "Optional",

    // Clip Selection Panel
    clipSelection: "Clip Selection",
    videoGenerationDesc: "Review and select generated videos for each clip",
    backToStoryboard: "Back to Storyboard",
    videoNotPlayable: "Cannot play this video.",
    generatingWith: (model: string) => `Generating with ${model}...`,
    noVideosForClip: "No videos generated for this clip",
    selectVideoPrompt: "Select a video below",
    generatedVideos: (count: number) => `Generated Videos (${count})`,
    clipSelectionStatus: (selected: number, total: number) =>
      `${selected} / ${total} clips selected`,
    selected: "Selected",
    createFinalVideo: "Create Final Video",
    creating: "Creating...",
    creatingFinalVideo: "Creating Final Video...",
    creatingFinalVideoDesc: "Merging selected clips into one video",

    // Final Video Panel
    finalVideo: "Final Video",
    finalVideoDesc: "Review your completed ad video",
    backToSceneSelection: "Back to Scene Selection",
    videoReady: "Video Ready",
    pressPlayToWatch: "Press play to watch",
    videoComplete: "Your ad video is complete!",
    scenesJoined: "Selected scenes have been merged into one video",
    createAgain: "Create Again",
    download: "Download",
  },
} as const;

export type Translations = typeof translations.ko;

export function t(lang: Language): Translations {
  return translations[lang];
}

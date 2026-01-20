import clsx from "clsx";

type StoryboardPanelProps = {
  className?: string;
};

// 임시 데이터 타입 (추후 실제 데이터 모델로 교체)
type Scene = {
  sceneId: string;
  durationSec: number;
  description: string;
  transition: string;
  keyElements: string[];
};

// placeholder 데이터
const PLACEHOLDER_SCENES: Scene[] = [];

export function StoryboardPanel({ className }: StoryboardPanelProps) {
  const hasScenes = PLACEHOLDER_SCENES.length > 0;

  return (
    <div className={clsx("flex h-full w-full flex-col", className)}>
      {/* 헤더 */}
      <div className="border-b border-slate-200/80 px-6 py-4 dark:border-slate-700/60">
        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
          스토리보드
        </h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          광고 영상의 컷 구성을 확인하세요
        </p>
      </div>

      {/* 컨텐츠 영역 */}
      <div className="flex-1 overflow-y-auto p-6">
        {hasScenes ? (
          <div className="space-y-4">
            {PLACEHOLDER_SCENES.map((scene, index) => (
              <SceneCard key={scene.sceneId} scene={scene} index={index} />
            ))}
          </div>
        ) : (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-slate-100 dark:bg-slate-800">
                <svg
                  className="h-8 w-8 text-slate-400 dark:text-slate-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z"
                  />
                </svg>
              </div>
              <p className="text-slate-500 dark:text-slate-400">
                채팅에서 광고 요청을 입력하면
              </p>
              <p className="text-slate-500 dark:text-slate-400">
                스토리보드가 여기에 생성됩니다
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

type SceneCardProps = {
  scene: Scene;
  index: number;
};

function SceneCard({ scene, index }: SceneCardProps) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md dark:border-slate-700 dark:bg-slate-800/50">
      <div className="flex items-start gap-4">
        {/* 컷 번호 */}
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-sm font-bold text-slate-600 dark:bg-slate-700 dark:text-slate-300">
          {index + 1}
        </div>

        <div className="flex-1">
          {/* 설명 */}
          <p className="font-medium text-slate-800 dark:text-slate-100">
            {scene.description}
          </p>

          {/* 메타 정보 */}
          <div className="mt-2 flex flex-wrap gap-2">
            <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
              {scene.durationSec}초
            </span>
            {scene.keyElements.map((element) => (
              <span
                key={element}
                className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-700 dark:text-slate-300"
              >
                {element}
              </span>
            ))}
          </div>

          {/* 전환 효과 */}
          {scene.transition && (
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              전환: {scene.transition}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

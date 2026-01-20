import clsx from "clsx";
import { useState } from "react";

import { useAppStore } from "../store/useAppStore";
import type { VideoCandidate, Translations } from "../types";
import { MOCK_CLIPS, MOCK_VIDEO_CANDIDATES } from "../lib/mockData";
import { t } from "../lib/i18n";
import {
  Button,
  PanelLayout,
  PanelContent,
  PanelFooter,
  Spinner,
  StatusDot,
  LoadingState,
} from "./ui";

type ClipSelectionPanelProps = {
  className?: string;
};

export function ClipSelectionPanel({ className }: ClipSelectionPanelProps) {
  const setRightPanel = useAppStore((state) => state.setRightPanel);
  const selectedVideoIds = useAppStore((state) => state.selectedVideoIds);
  const isCreatingFinalVideo = useAppStore((state) => state.isCreatingFinalVideo);
  const setIsCreatingFinalVideo = useAppStore((state) => state.setIsCreatingFinalVideo);
  const language = useAppStore((state) => state.language);
  const i18n = t(language);

  const handleCreateFinalVideo = async () => {
    setIsCreatingFinalVideo(true);
    await new Promise((resolve) => setTimeout(resolve, 2000));
    setIsCreatingFinalVideo(false);
    setRightPanel("final");
  };

  return (
    <PanelLayout className={className}>
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between border-b border-slate-200 px-5 py-3 dark:border-slate-700">
        <h2 className="text-base font-semibold text-slate-900 dark:text-white">
          {i18n.clipSelection}
        </h2>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setRightPanel("storyboard")}
          disabled={isCreatingFinalVideo}
        >
          {i18n.backToStoryboard}
        </Button>
      </div>

      <PanelContent className="overflow-y-auto">
        {isCreatingFinalVideo ? (
          <LoadingState
            title={i18n.creatingFinalVideo}
            description={i18n.creatingFinalVideoDesc}
          />
        ) : (
          <div className="space-y-2">
            {MOCK_CLIPS.map((clip) => (
              <CollapsibleClipRow
                key={clip.index}
                clipIndex={clip.index}
                sceneDescription={clip.scene_description}
                duration={clip.duration}
                i18n={i18n}
              />
            ))}
          </div>
        )}
      </PanelContent>

      <PanelFooter className="flex items-center justify-between">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          {i18n.clipSelectionStatus(Object.keys(selectedVideoIds).length, MOCK_CLIPS.length)}
        </p>
        <Button onClick={handleCreateFinalVideo} loading={isCreatingFinalVideo}>
          {isCreatingFinalVideo ? i18n.creating : i18n.createFinalVideo}
        </Button>
      </PanelFooter>
    </PanelLayout>
  );
}

// ============================================
// Collapsible Clip Row
// ============================================

type CollapsibleClipRowProps = {
  clipIndex: number;
  sceneDescription: string;
  duration: number;
  i18n: Translations;
};

function CollapsibleClipRow({ clipIndex, sceneDescription, duration, i18n }: CollapsibleClipRowProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const selectedVideoIds = useAppStore((state) => state.selectedVideoIds);
  const selectVideo = useAppStore((state) => state.selectVideo);

  const candidates = MOCK_VIDEO_CANDIDATES.filter((c) => c.clipIndex === clipIndex);
  const selectedVideoId = selectedVideoIds[clipIndex];
  const selectedVideo = selectedVideoId ? candidates.find((c) => c.id === selectedVideoId) : undefined;
  const hasSelection = selectedVideoId !== undefined;

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
      {/* Collapsed Header - Always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-slate-50 dark:hover:bg-slate-700/50"
      >
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-slate-900 text-xs font-semibold text-white dark:bg-slate-600">
          {clipIndex + 1}
        </span>

        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-slate-800 dark:text-slate-100">
            {sceneDescription || "씬 설명 없음"}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {hasSelection && (
            <span className="flex items-center gap-1 rounded bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400">
              <CheckIcon className="h-3 w-3" />
              {i18n.selected}
            </span>
          )}
          <span className="text-xs text-slate-500 dark:text-slate-400">
            {duration}{i18n.seconds}
          </span>
          <ChevronIcon
            className={clsx(
              "h-4 w-4 text-slate-400 transition-transform dark:text-slate-500",
              isExpanded && "rotate-180"
            )}
          />
        </div>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="border-t border-slate-100 bg-slate-50/50 p-4 dark:border-slate-700 dark:bg-slate-800/50">
          {/* Selected Video Preview */}
          {selectedVideo ? (
            <VideoPreview video={selectedVideo} i18n={i18n} />
          ) : (
            <div className="flex aspect-video w-full items-center justify-center rounded-xl border-2 border-dashed border-slate-200 bg-slate-50 dark:border-slate-600 dark:bg-slate-800">
              <p className="text-sm text-slate-400 dark:text-slate-500">
                {i18n.selectVideoPrompt}
              </p>
            </div>
          )}

          {/* Video Candidates Grid */}
          <div className="mt-4">
            <h4 className="mb-2 text-xs font-medium text-slate-600 dark:text-slate-300">
              {i18n.generatedVideos(candidates.length)}
            </h4>
            <div className="grid grid-cols-3 gap-2">
              {candidates.map((candidate) => (
                <VideoThumbnail
                  key={candidate.id}
                  candidate={candidate}
                  isSelected={selectedVideo?.id === candidate.id}
                  onSelect={() => selectVideo(clipIndex, candidate.id)}
                />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================
// Sub-components
// ============================================

type VideoPreviewProps = {
  video: VideoCandidate | undefined;
  i18n: Translations;
};

function VideoPreview({ video, i18n }: VideoPreviewProps) {
  if (!video) {
    return (
      <div className="flex aspect-video w-full items-center justify-center rounded-xl bg-slate-100 dark:bg-slate-800">
        <p className="text-slate-500 dark:text-slate-400">
          {i18n.noVideosForClip}
        </p>
      </div>
    );
  }

  return (
    <div className="aspect-video w-full overflow-hidden rounded-xl bg-slate-900">
      {video.status === "completed" ? (
        <video
          key={video.id}
          className="h-full w-full object-contain"
          controls
          autoPlay
          muted
          loop
        >
          <source src={video.url} type="video/mp4" />
          {i18n.videoNotPlayable}
        </video>
      ) : (
        <div className="flex h-full w-full items-center justify-center">
          <div className="text-center">
            <Spinner size="md" className="mx-auto mb-3" />
            <p className="text-sm text-slate-400">{i18n.generatingWith(video.model)}</p>
          </div>
        </div>
      )}
    </div>
  );
}

type VideoThumbnailProps = {
  candidate: VideoCandidate;
  isSelected: boolean;
  onSelect: () => void;
};

function VideoThumbnail({ candidate, isSelected, onSelect }: VideoThumbnailProps) {
  return (
    <button
      onClick={onSelect}
      className={clsx(
        "group relative aspect-video overflow-hidden rounded-lg border-2 transition-all",
        isSelected
          ? "border-slate-900 ring-2 ring-slate-300 dark:border-slate-100 dark:ring-slate-600"
          : "border-slate-200 hover:border-slate-300 dark:border-slate-700 dark:hover:border-slate-600"
      )}
    >
      <div className="absolute inset-0 bg-slate-200 dark:bg-slate-700">
        {candidate.status === "completed" && (
          <video
            className="h-full w-full object-cover"
            src={candidate.url}
            muted
            preload="metadata"
          />
        )}
        {candidate.status === "generating" && (
          <div className="flex h-full w-full items-center justify-center">
            <Spinner size="sm" />
          </div>
        )}
      </div>

      {/* 모델 라벨 */}
      <div className="absolute bottom-1 left-1 flex items-center gap-1 rounded bg-black/60 px-1.5 py-0.5 text-xs text-white">
        <StatusDot status={candidate.status} />
        {candidate.model}
      </div>

      {/* 선택 체크마크 */}
      {isSelected && (
        <div className="absolute right-1 top-1 flex h-5 w-5 items-center justify-center rounded-full bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900">
          <CheckIcon className="h-3 w-3" />
        </div>
      )}
    </button>
  );
}

// ============================================
// Icons
// ============================================

function ChevronIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
    </svg>
  );
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="currentColor" viewBox="0 0 20 20">
      <path
        fillRule="evenodd"
        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
        clipRule="evenodd"
      />
    </svg>
  );
}

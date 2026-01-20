import clsx from "clsx";
import { useState, useRef, useEffect } from "react";

import { useAppStore } from "../store/useAppStore";
import type { Clip, VeoClip, ImageInput, Translations } from "../types";
import { t } from "../lib/i18n";
import {
  Button,
  PanelLayout,
  PanelContent,
  PanelFooter,
  EmptyState,
  LoadingState,
} from "./ui";

type StoryboardPanelProps = {
  className?: string;
};

export function StoryboardPanel({ className }: StoryboardPanelProps) {
  const storyboard = useAppStore((state) => state.storyboard);
  const setRightPanel = useAppStore((state) => state.setRightPanel);
  const isGeneratingVideos = useAppStore((state) => state.isGeneratingVideos);
  const setIsGeneratingVideos = useAppStore(
    (state) => state.setIsGeneratingVideos
  );
  const updateStoryboardDescription = useAppStore(
    (state) => state.updateStoryboardDescription
  );
  const language = useAppStore((state) => state.language);
  const i18n = t(language);

  const hasClips = storyboard && storyboard.clips.length > 0;
  const canGenerate = true;

  const handleGenerateVideos = async () => {
    setIsGeneratingVideos(true);
    await new Promise((resolve) => setTimeout(resolve, 2000));
    setIsGeneratingVideos(false);
    setRightPanel("video");
  };

  return (
    <PanelLayout className={className}>
      {/* Header */}
      <div className="shrink-0 border-b border-slate-200 px-5 py-3 dark:border-slate-700">
        <h2 className="text-base font-semibold text-slate-900 dark:text-white">
          {i18n.storyboard}
        </h2>
      </div>

      {/* Description & Duration - Below header */}
      {storyboard && !isGeneratingVideos && (
        <div className="shrink-0 border-b border-slate-200 bg-slate-50/50 px-5 py-4 dark:border-slate-700 dark:bg-slate-800/30">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
              {i18n.videoDescription}
            </span>
            <div className="flex items-center gap-1.5 rounded-full bg-slate-200/80 px-2.5 py-0.5 dark:bg-slate-700">
              <ClockIcon className="h-3 w-3 text-slate-500 dark:text-slate-400" />
              <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
                {storyboard.clips.reduce((sum, clip) => sum + clip.duration, 0)}{i18n.seconds}
              </span>
            </div>
          </div>
          <textarea
            value={storyboard.description}
            onChange={(e) => updateStoryboardDescription(e.target.value)}
            className="w-full resize-none rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm leading-relaxed text-slate-700 transition-colors placeholder:text-slate-400 hover:border-slate-300 focus:border-slate-400 focus:outline-none dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200 dark:hover:border-slate-500 dark:focus:border-slate-500"
            rows={3}
            placeholder={i18n.videoDescription}
          />
        </div>
      )}

      <PanelContent className="overflow-y-auto">
        {isGeneratingVideos ? (
          <LoadingState
            title={i18n.generatingVideos}
            description={i18n.generatingVideosDesc}
          />
        ) : hasClips ? (
          <div className="space-y-2">
            {storyboard.clips.map((clip, index) => (
              <CollapsibleClipCard
                key={index}
                clip={clip}
                index={index}
                i18n={i18n}
              />
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<StoryboardIcon />}
            title={i18n.chatPrompt1}
            description={i18n.chatPrompt2}
          />
        )}
      </PanelContent>

      <PanelFooter className="flex justify-end">
        <Button
          onClick={handleGenerateVideos}
          disabled={!canGenerate}
          loading={isGeneratingVideos}
        >
          {isGeneratingVideos ? i18n.generating : i18n.generate}
        </Button>
      </PanelFooter>
    </PanelLayout>
  );
}

// ============================================
// Collapsible Clip Card
// ============================================

type CollapsibleClipCardProps = {
  clip: Clip;
  index: number;
  i18n: Translations;
};

function CollapsibleClipCard({ clip, index, i18n }: CollapsibleClipCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const updateClip = useAppStore((state) => state.updateClip);
  const originalStoryboard = useAppStore((state) => state.originalStoryboard);
  const originalClip = originalStoryboard?.clips[index];

  const handleFieldChange = (field: keyof Clip, value: string | number) => {
    updateClip(index, { [field]: value } as Partial<Clip>);
  };

  const isVeoClip = clip.provider === "veo";
  const veoClip = isVeoClip ? (clip as VeoClip) : null;

  const modelLabel = clip.provider === "sora" ? "Sora 2 Pro" : "Veo 3";

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800">
      {/* Collapsed Header - Always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-slate-50 dark:hover:bg-slate-700/50"
      >
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-slate-900 text-xs font-semibold text-white dark:bg-slate-600">
          {index + 1}
        </span>

        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-slate-800 dark:text-slate-100">
            {clip.scene_description || "씬 설명 없음"}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-700 dark:text-slate-300">
            {modelLabel}
          </span>
          <span className="text-xs text-slate-500 dark:text-slate-400">
            {clip.duration}{i18n.seconds}
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
          {/* Top Row: Model & Duration */}
          <div className="mb-4 flex items-center gap-3">
            <ModelSelector
              provider={clip.provider}
              onChange={(provider) => handleFieldChange("provider", provider)}
            />
            <DurationSelector
              value={clip.duration}
              onChange={(d) => handleFieldChange("duration", d)}
              suffix={i18n.seconds}
            />
          </div>

          {/* Text Fields */}
          <div className="space-y-3">
            <FieldGroup
              label={i18n.sceneDescription}
              onReset={
                originalClip && clip.scene_description !== originalClip.scene_description
                  ? () => handleFieldChange("scene_description", originalClip.scene_description)
                  : undefined
              }
            >
              <textarea
                value={clip.scene_description}
                onChange={(e) =>
                  handleFieldChange("scene_description", e.target.value)
                }
                rows={2}
                className="w-full resize-none rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 hover:border-slate-300 focus:border-slate-400 focus:outline-none dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200"
              />
            </FieldGroup>

            <FieldGroup
              label={i18n.prompt}
              onReset={
                originalClip && clip.prompt !== originalClip.prompt
                  ? () => handleFieldChange("prompt", originalClip.prompt)
                  : undefined
              }
            >
              <textarea
                value={clip.prompt}
                onChange={(e) => handleFieldChange("prompt", e.target.value)}
                rows={3}
                className="w-full resize-none rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 hover:border-slate-300 focus:border-slate-400 focus:outline-none dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200"
              />
            </FieldGroup>
          </div>

          {/* Image Fields - 3 columns */}
          <div className="mt-4 grid grid-cols-3 gap-3">
            <FieldGroup label={i18n.inputImage}>
              <ImageField
                image={clip.input_image}
                onChange={(img) =>
                  updateClip(index, { input_image: img } as Partial<Clip>)
                }
                i18n={i18n}
              />
            </FieldGroup>

            <FieldGroup label={i18n.lastFrame} optional i18n={i18n}>
              <ImageField
                image={isVeoClip ? veoClip?.last_frame : undefined}
                onChange={(img) =>
                  updateClip(index, { last_frame: img } as Partial<VeoClip>)
                }
                i18n={i18n}
                disabled={!isVeoClip}
              />
            </FieldGroup>

            <FieldGroup label={i18n.referenceImages} optional i18n={i18n}>
              <ReferenceImagesField
                images={isVeoClip ? veoClip?.reference_images : undefined}
                onChange={(imgs) =>
                  updateClip(index, {
                    reference_images: imgs,
                  } as Partial<VeoClip>)
                }
                disabled={!isVeoClip}
                i18n={i18n}
              />
            </FieldGroup>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================
// Helper Components
// ============================================

type FieldGroupProps = {
  label: string;
  children: React.ReactNode;
  optional?: boolean;
  onReset?: () => void;
  i18n?: Translations;
};

function FieldGroup({ label, children, optional, onReset, i18n }: FieldGroupProps) {
  return (
    <div>
      <div className="mb-1.5 flex items-center gap-1.5">
        <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
          {label}
        </span>
        {optional && (
          <span className="text-[10px] text-slate-400 dark:text-slate-500">
            ({i18n?.optional || "선택"})
          </span>
        )}
        {onReset && (
          <button
            onClick={onReset}
            className="ml-auto flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] text-slate-500 hover:bg-slate-200 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-600 dark:hover:text-slate-200"
            title="초기화"
          >
            <ResetIcon className="h-3 w-3" />
            <span>초기화</span>
          </button>
        )}
      </div>
      {children}
    </div>
  );
}

type ImageFieldProps = {
  image?: ImageInput;
  onChange: (image?: ImageInput) => void;
  i18n: Translations;
  disabled?: boolean;
};

function ImageField({ image, onChange, i18n, disabled }: ImageFieldProps) {
  const [isDragging, setIsDragging] = useState(false);

  if (disabled) {
    return (
      <div className="flex aspect-video items-center justify-center rounded-lg border border-slate-200 bg-slate-100 dark:border-slate-700 dark:bg-slate-800">
        <span className="text-[11px] text-slate-400 dark:text-slate-500">{i18n.veoOnly}</span>
      </div>
    );
  }

  const handleFile = (file: File) => {
    if (!file.type.startsWith("image/")) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      const base64 = e.target?.result as string;
      const mimeType = file.type as "image/jpeg" | "image/png" | "image/webp";
      onChange({ base64, mime_type: mimeType });
    };
    reader.readAsDataURL(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleClick = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) handleFile(file);
    };
    input.click();
  };

  const hasImage = image?.url || image?.base64;

  return (
    <div>
      {hasImage ? (
        <div className="group relative aspect-video overflow-hidden rounded-lg border border-slate-200 bg-slate-100 dark:border-slate-600 dark:bg-slate-700">
          <img
            src={image?.base64 || image?.url}
            alt="Preview"
            className="h-full w-full object-cover"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
          <button
            onClick={() => onChange(undefined)}
            className="absolute right-1.5 top-1.5 flex h-6 w-6 items-center justify-center rounded-full bg-black/60 text-white opacity-0 transition-opacity hover:bg-black/80 group-hover:opacity-100"
          >
            <XIcon className="h-3.5 w-3.5" />
          </button>
        </div>
      ) : (
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={handleClick}
          className={clsx(
            "flex aspect-video cursor-pointer items-center justify-center rounded-lg border-2 border-dashed transition-colors",
            isDragging
              ? "border-slate-400 bg-slate-100 dark:border-slate-500 dark:bg-slate-700"
              : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-700 dark:hover:border-slate-500"
          )}
        >
          <div className="text-center">
            <UploadIcon className="mx-auto h-5 w-5 text-slate-400 dark:text-slate-500" />
            <span className="mt-1 block text-[11px] text-slate-400 dark:text-slate-500">
              {i18n.noImage}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

type ReferenceImagesFieldProps = {
  images?: ImageInput[];
  onChange: (images?: ImageInput[]) => void;
  disabled?: boolean;
  i18n: Translations;
};

function ReferenceImagesField({ images, onChange, disabled, i18n }: ReferenceImagesFieldProps) {
  const [isDragging, setIsDragging] = useState(false);

  if (disabled) {
    return (
      <div className="flex h-16 items-center justify-center rounded-lg border border-slate-200 bg-slate-100 dark:border-slate-700 dark:bg-slate-800">
        <span className="text-[11px] text-slate-400 dark:text-slate-500">{i18n.veoOnly}</span>
      </div>
    );
  }

  const handleFiles = (files: FileList) => {
    const newImages: ImageInput[] = [];
    let processed = 0;

    Array.from(files).forEach((file) => {
      if (!file.type.startsWith("image/")) {
        processed++;
        return;
      }

      const reader = new FileReader();
      reader.onload = (e) => {
        const base64 = e.target?.result as string;
        const mimeType = file.type as "image/jpeg" | "image/png" | "image/webp";
        newImages.push({ base64, mime_type: mimeType });
        processed++;

        if (processed === files.length && newImages.length > 0) {
          onChange([...(images || []), ...newImages]);
        }
      };
      reader.readAsDataURL(file);
    });
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleClick = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.multiple = true;
    input.onchange = (e) => {
      const files = (e.target as HTMLInputElement).files;
      if (files && files.length > 0) handleFiles(files);
    };
    input.click();
  };

  const removeImage = (idx: number) => {
    const newImages = (images || []).filter((_, i) => i !== idx);
    onChange(newImages.length > 0 ? newImages : undefined);
  };

  return (
    <div className="space-y-2">
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={handleClick}
        className={clsx(
          "flex h-12 cursor-pointer items-center justify-center rounded-lg border-2 border-dashed transition-colors",
          isDragging
            ? "border-slate-400 bg-slate-100 dark:border-slate-500 dark:bg-slate-700"
            : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-700 dark:hover:border-slate-500"
        )}
      >
        <div className="flex items-center gap-2 text-slate-400 dark:text-slate-500">
          <UploadIcon className="h-4 w-4" />
          <span className="text-xs">이미지 추가</span>
        </div>
      </div>

      {images && images.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {images.map((img, idx) => (
            <div
              key={idx}
              className="group relative h-14 w-14 overflow-hidden rounded-lg border border-slate-200 dark:border-slate-600"
            >
              <img
                src={img.base64 || img.url}
                alt={`Ref ${idx + 1}`}
                className="h-full w-full object-cover"
              />
              <button
                onClick={() => removeImage(idx)}
                className="absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 transition-opacity group-hover:opacity-100"
              >
                <XIcon className="h-4 w-4 text-white" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

type ModelSelectorProps = {
  provider: "sora" | "veo";
  onChange: (provider: "sora" | "veo") => void;
};

function ModelSelector({ provider, onChange }: ModelSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const models = [
    { value: "veo" as const, label: "Veo 3" },
    { value: "sora" as const, label: "Sora 2 Pro" },
  ];

  const currentLabel = provider === "sora" ? "Sora 2 Pro" : "Veo 3";

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex h-9 items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600"
      >
        <span>{currentLabel}</span>
        <ChevronIcon className={clsx("h-4 w-4 text-slate-400 transition-transform", isOpen && "rotate-180")} />
      </button>

      {isOpen && (
        <div className="absolute left-0 top-full z-50 mt-1 min-w-[140px] overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg dark:border-slate-600 dark:bg-slate-800">
          {models.map((m) => (
            <button
              key={m.value}
              onClick={() => {
                onChange(m.value);
                setIsOpen(false);
              }}
              className={clsx(
                "flex w-full items-center px-3 py-2 text-left text-sm transition-colors",
                provider === m.value
                  ? "bg-slate-100 font-medium text-slate-900 dark:bg-slate-700 dark:text-white"
                  : "text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-700"
              )}
            >
              {m.label}
              {provider === m.value && <CheckIcon className="ml-auto h-4 w-4" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

type DurationSelectorProps = {
  value: number;
  onChange: (value: number) => void;
  suffix: string;
};

function DurationSelector({ value, onChange, suffix }: DurationSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const durations = [4, 8, 16];

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex h-9 items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600"
      >
        <ClockIcon className="h-4 w-4 text-slate-400" />
        <span>{value}{suffix}</span>
        <ChevronIcon className={clsx("h-4 w-4 text-slate-400 transition-transform", isOpen && "rotate-180")} />
      </button>

      {isOpen && (
        <div className="absolute left-0 top-full z-50 mt-1 min-w-[100px] overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg dark:border-slate-600 dark:bg-slate-800">
          {durations.map((d) => (
            <button
              key={d}
              onClick={() => {
                onChange(d);
                setIsOpen(false);
              }}
              className={clsx(
                "flex w-full items-center justify-between px-3 py-2 text-left text-sm transition-colors",
                value === d
                  ? "bg-slate-100 font-medium text-slate-900 dark:bg-slate-700 dark:text-white"
                  : "text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-700"
              )}
            >
              <span>{d}{suffix}</span>
              {value === d && <CheckIcon className="h-4 w-4" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}


// ============================================
// Icons
// ============================================

function ClockIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 6v6l4 2m6-2a10 10 0 11-20 0 10 10 0 0120 0z"
      />
    </svg>
  );
}

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

function StoryboardIcon() {
  return (
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
  );
}

function XIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M6 18L18 6M6 6l12 12"
      />
    </svg>
  );
}

function ImageIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
      />
    </svg>
  );
}

function UploadIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
      />
    </svg>
  );
}

function ResetIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
      />
    </svg>
  );
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  );
}

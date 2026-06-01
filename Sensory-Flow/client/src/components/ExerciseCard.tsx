import { useState, useRef } from "react";
import { 
  Upload, 
  Video, 
  Scissors, 
  Check, 
  X, 
  Play, 
  Pause,
  RotateCcw,
  Loader2,
  AlertCircle
} from "lucide-react";

import type { ExerciseVideoData, ExerciseType } from "@shared/schema";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { cn } from "@/lib/utils";

interface ExerciseCardProps {
  exercise: ExerciseType;
  videoData: ExerciseVideoData;
  onUpload: (file: File) => void;
  onTrimSave: (start: number, end: number) => void;
  onRemove: () => void;
  observation?: string;
  onObservationChange?: (value: string) => void;
}

export function ExerciseCard({
  exercise,
  videoData,
  onUpload,
  onTrimSave,
  onRemove,
  observation,
  onObservationChange,
}: ExerciseCardProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [trimStart, setTrimStart] = useState(0);
  const [trimEnd, setTrimEnd] = useState(0);
  const [isTrimming, setIsTrimming] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const validTypes = ["video/mp4", "video/quicktime", "video/mov"];
      if (validTypes.includes(file.type) || file.name.endsWith(".mov")) {
        onUpload(file);
      } else {
        alert("Please upload MP4 or MOV video files only.");
      }
    }
  };

  const handleVideoLoad = () => {
    if (videoRef.current) {
      const dur = videoRef.current.duration;
      setDuration(dur);
      setTrimEnd(dur);
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const togglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleTrimChange = (values: number[]) => {
    setTrimStart(values[0]);
    setTrimEnd(values[1]);
    if (videoRef.current) {
      videoRef.current.currentTime = values[0];
    }
  };

  const saveTrim = () => {
    onTrimSave(trimStart, trimEnd);
    setIsTrimming(false);
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const getStatusColor = () => {
    switch (videoData.status) {
      case "ready":
        return "bg-green-500";
      case "uploading":
      case "trimming":
      case "processing":
        return "bg-yellow-500";
      case "error":
        return "bg-red-500";
      default:
        return "bg-muted-foreground/30";
    }
  };

  const getStatusText = () => {
    switch (videoData.status) {
      case "empty":
        return "Not uploaded";
      case "uploading":
        return "Uploading...";
      case "uploaded":
        return "Uploaded - Trim Required";
      case "trimming":
        return "Trimming...";
      case "ready":
        return "Ready for Processing";
      case "processing":
        return "Processing...";
      case "completed":
        return "Completed";
      case "error":
        return "Error";
      default:
        return "Unknown";
    }
  };

  return (
    <Card 
      className="overflow-hidden"
      data-testid={`card-exercise-${exercise.id}`}
    >
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary/10 flex-shrink-0">
              <Video className="w-5 h-5 text-primary" />
            </div>
            <div className="min-w-0">
              <h3 className="font-medium text-foreground truncate">{exercise.name}</h3>
              <p className="text-xs text-muted-foreground truncate">{exercise.description}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <div className={cn("w-2 h-2 rounded-full", getStatusColor())} />
            <span className="text-xs text-muted-foreground whitespace-nowrap">{getStatusText()}</span>
          </div>
        </div>
      </div>

      <div className="p-4">
        {videoData.status === "empty" && (
          <div
            className="border-2 border-dashed border-border rounded-lg p-8 text-center cursor-pointer hover:border-primary/50 transition-colors"
            onClick={() => fileInputRef.current?.click()}
            data-testid={`upload-area-${exercise.id}`}
          >
            <Upload className="w-10 h-10 mx-auto text-muted-foreground mb-3" />
            <p className="text-sm font-medium text-foreground mb-1">
              Drag & drop or click to upload
            </p>
            <p className="text-xs text-muted-foreground">
              Supported formats: MP4, MOV (Max 500MB)
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept="video/mp4,video/quicktime,.mov,.mp4"
              className="hidden"
              onChange={handleFileChange}
              data-testid={`input-file-${exercise.id}`}
            />
          </div>
        )}

        {videoData.status === "uploading" && (
          <div className="flex flex-col items-center justify-center p-8">
            <Loader2 className="w-10 h-10 text-primary animate-spin mb-3" />
            <p className="text-sm text-muted-foreground">Uploading video...</p>
          </div>
        )}

        {(videoData.status === "uploaded" || videoData.status === "ready" || isTrimming) && videoData.videoUrl && (
          <div className="space-y-4">
            <div className="relative aspect-video bg-black rounded-lg overflow-hidden">
              <video
                ref={videoRef}
                src={videoData.videoUrl}
                className="w-full h-full object-contain"
                onLoadedMetadata={handleVideoLoad}
                onTimeUpdate={handleTimeUpdate}
                onEnded={() => setIsPlaying(false)}
                data-testid={`video-preview-${exercise.id}`}
              />
              <Button
                size="icon"
                variant="secondary"
                className="absolute bottom-3 left-3"
                onClick={togglePlay}
                data-testid={`button-play-${exercise.id}`}
              >
                {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              </Button>
              <div className="absolute bottom-3 right-3 bg-black/70 text-white text-xs px-2 py-1 rounded">
                {formatTime(currentTime)} / {formatTime(duration)}
              </div>
            </div>

            {isTrimming ? (
              <div className="space-y-4 p-4 bg-muted/50 rounded-lg">
                <div className="flex items-center gap-2 text-sm">
                  <Scissors className="w-4 h-4 text-primary" />
                  <span className="font-medium">Trim Video</span>
                </div>
                <div className="space-y-2">
                  <Slider
                    value={[trimStart, trimEnd]}
                    min={0}
                    max={duration || 100}
                    step={0.1}
                    onValueChange={handleTrimChange}
                    className="w-full"
                    data-testid={`slider-trim-${exercise.id}`}
                  />
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>Start: {formatTime(trimStart)}</span>
                    <span>Duration: {formatTime(trimEnd - trimStart)}</span>
                    <span>End: {formatTime(trimEnd)}</span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button 
                    size="sm" 
                    onClick={saveTrim}
                    data-testid={`button-save-trim-${exercise.id}`}
                  >
                    <Check className="w-4 h-4 mr-1" />
                    Save Trim
                  </Button>
                  <Button 
                    size="sm" 
                    variant="outline" 
                    onClick={() => setIsTrimming(false)}
                    data-testid={`button-cancel-trim-${exercise.id}`}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                <Button 
                  size="sm" 
                  variant="outline" 
                  onClick={() => setIsTrimming(true)}
                  data-testid={`button-trim-${exercise.id}`}
                >
                  <Scissors className="w-4 h-4 mr-1" />
                  Trim
                </Button>
                <Button 
                  size="sm" 
                  variant="outline" 
                  onClick={() => fileInputRef.current?.click()}
                  data-testid={`button-replace-${exercise.id}`}
                >
                  <RotateCcw className="w-4 h-4 mr-1" />
                  Replace
                </Button>
                <Button 
                  size="sm" 
                  variant="outline" 
                  onClick={onRemove}
                  data-testid={`button-remove-${exercise.id}`}
                >
                  <X className="w-4 h-4 mr-1" />
                  Remove
                </Button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="video/mp4,video/quicktime,.mov,.mp4"
                  className="hidden"
                  onChange={handleFileChange}
                />
              </div>
            )}

            {videoData.status === "ready" && (
              <div className="flex items-center gap-2 p-3 bg-green-500/10 rounded-lg border border-green-500/20">
                <Check className="w-4 h-4 text-green-600" />
                <span className="text-sm text-green-700 dark:text-green-400">
                  Video is ready for processing
                </span>
              </div>
            )}
          </div>
        )}

        {videoData.status === "processing" && (
          <div className="flex flex-col items-center justify-center p-8">
            <Loader2 className="w-10 h-10 text-primary animate-spin mb-3" />
            <p className="text-sm text-muted-foreground">AI is analyzing the video...</p>
          </div>
        )}

        {videoData.status === "error" && (
          <div className="flex flex-col items-center justify-center p-8">
            <AlertCircle className="w-10 h-10 text-destructive mb-3" />
            <p className="text-sm text-destructive">An error occurred</p>
            <Button 
              size="sm" 
              variant="outline" 
              className="mt-3" 
              onClick={() => fileInputRef.current?.click()}
            >
              Try Again
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept="video/mp4,video/quicktime,.mov,.mp4"
              className="hidden"
              onChange={handleFileChange}
            />
          </div>
        )}

        {videoData.status === "completed" && videoData.result && (
          <div className="p-4 bg-green-500/10 rounded-lg border border-green-500/20 space-y-3">
            <div className="flex items-center gap-2 mb-1">
              <Check className="w-4 h-4 text-green-600" />
              <span className="text-sm font-medium text-green-700 dark:text-green-400">
                Analysis Complete
              </span>
            </div>

            {videoData.result.totalScore !== undefined &&
              videoData.result.maxScore !== undefined && (
                <p className="text-sm font-medium text-foreground">
                  Score: {videoData.result.totalScore}/{videoData.result.maxScore}
                </p>
              )}

            {/* Score breakdown */}
            {videoData.result.scores &&
              Object.keys(videoData.result.scores).length > 0 && (
                <div className="text-xs text-muted-foreground space-y-1">
                  <p className="text-xs font-semibold text-foreground">
                    Score breakdown
                  </p>
                  {Object.entries(videoData.result.scores).map(
                    ([name, value]) => (
                      <p key={name}>
                        {name}: {value}
                      </p>
                    ),
                  )}
                </div>
              )}

            {/* Raw parameter values */}
            {videoData.result.rawMetrics &&
              Object.keys(videoData.result.rawMetrics).length > 0 && (
                <div className="text-xs text-muted-foreground space-y-1">
                  <p className="text-xs font-semibold text-foreground">
                    Raw parameters
                  </p>
                  {Object.entries(videoData.result.rawMetrics).map(
                    ([name, value]) => {
                      let display: string;
                      if (typeof value === "number") {
                        display = Number.isFinite(value)
                          ? value.toFixed(3)
                          : String(value);
                      } else {
                        display = String(value);
                      }
                      return (
                        <p key={name}>
                          {name}: {display}
                        </p>
                      );
                    },
                  )}
                </div>
              )}
          </div>
        )}
      </div>

      {/* Additional observation inputs for Prone/Supine */}
      {onObservationChange && (exercise.id === "prone_extension" || exercise.id === "supine_flexion") && (
        <div className="px-4 pb-4 border-t border-border pt-3">
          <p className="text-sm font-semibold text-foreground mb-2">
            {exercise.id === "prone_extension"
              ? "Ability to assume prone extension"
              : "Ability to assume supine flexion"}
          </p>
          <div className="flex flex-col gap-1.5">
            {[
              { value: "Unable to assume", label: "Unable to assume" },
              { value: "Assumes segmentally", label: "Assumes segmentally" },
              { value: "Assumes simultaneously", label: "Assumes simultaneously" },
            ].map((opt) => (
              <label key={opt.value} className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="radio"
                  name={`obs-${exercise.id}`}
                  value={opt.value}
                  checked={observation === opt.value}
                  onChange={() => onObservationChange(opt.value)}
                  className="accent-primary"
                />
                {opt.label}
              </label>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

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
import { exerciseVideoRequirements } from "@shared/schema";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

interface DualVideoExerciseCardProps {
  exercise: ExerciseType;
  videoData: ExerciseVideoData;
  onUploadFront: (file: File) => void;
  onUploadSide: (file: File) => void;
  onTrimSave: (side: "front" | "side", start: number, end: number) => void;
  onRemove: (side: "front" | "side") => void;
  onProcess: () => Promise<void>;
}

export function DualVideoExerciseCard({ 
  exercise, 
  videoData, 
  onUploadFront,
  onUploadSide,
  onTrimSave, 
  onRemove,
  onProcess
}: DualVideoExerciseCardProps) {
  const requirements = exerciseVideoRequirements[exercise.id] || { front: false, side: false };
  const [isPlayingFront, setIsPlayingFront] = useState(false);
  const [isPlayingSide, setIsPlayingSide] = useState(false);
  const [currentTimeFront, setCurrentTimeFront] = useState(0);
  const [currentTimeSide, setCurrentTimeSide] = useState(0);
  const [durationFront, setDurationFront] = useState(0);
  const [durationSide, setDurationSide] = useState(0);
  const [trimStartFront, setTrimStartFront] = useState(0);
  const [trimEndFront, setTrimEndFront] = useState(0);
  const [trimStartSide, setTrimStartSide] = useState(0);
  const [trimEndSide, setTrimEndSide] = useState(0);
  const [isTrimmingFront, setIsTrimmingFront] = useState(false);
  const [isTrimmingSide, setIsTrimmingSide] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  
  const videoRefFront = useRef<HTMLVideoElement>(null);
  const videoRefSide = useRef<HTMLVideoElement>(null);
  const fileInputFrontRef = useRef<HTMLInputElement>(null);
  const fileInputSideRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>, side: "front" | "side") => {
    const file = e.target.files?.[0];
    if (file) {
      const validTypes = ["video/mp4", "video/quicktime", "video/mov"];
      if (validTypes.includes(file.type) || file.name.endsWith(".mov")) {
        if (side === "front") {
          onUploadFront(file);
        } else {
          onUploadSide(file);
        }
      } else {
        alert("Please upload MP4 or MOV video files only.");
      }
    }
  };

  const handleVideoLoadFront = () => {
    if (videoRefFront.current) {
      const dur = videoRefFront.current.duration;
      setDurationFront(dur);
      setTrimEndFront(dur);
    }
  };

  const handleVideoLoadSide = () => {
    if (videoRefSide.current) {
      const dur = videoRefSide.current.duration;
      setDurationSide(dur);
      setTrimEndSide(dur);
    }
  };

  const handleTimeUpdateFront = () => {
    if (videoRefFront.current) {
      setCurrentTimeFront(videoRefFront.current.currentTime);
    }
  };

  const handleTimeUpdateSide = () => {
    if (videoRefSide.current) {
      setCurrentTimeSide(videoRefSide.current.currentTime);
    }
  };

  const togglePlayFront = () => {
    if (videoRefFront.current) {
      if (isPlayingFront) {
        videoRefFront.current.pause();
      } else {
        videoRefFront.current.play();
      }
      setIsPlayingFront(!isPlayingFront);
    }
  };

  const togglePlaySide = () => {
    if (videoRefSide.current) {
      if (isPlayingSide) {
        videoRefSide.current.pause();
      } else {
        videoRefSide.current.play();
      }
      setIsPlayingSide(!isPlayingSide);
    }
  };

  const handleTrimChangeFront = (values: number[]) => {
    setTrimStartFront(values[0]);
    setTrimEndFront(values[1]);
    if (videoRefFront.current) {
      videoRefFront.current.currentTime = values[0];
    }
  };

  const handleTrimChangeSide = (values: number[]) => {
    setTrimStartSide(values[0]);
    setTrimEndSide(values[1]);
    if (videoRefSide.current) {
      videoRefSide.current.currentTime = values[0];
    }
  };

  const saveTrimFront = () => {
    onTrimSave("front", trimStartFront, trimEndFront);
    setIsTrimmingFront(false);
  };

  const saveTrimSide = () => {
    onTrimSave("side", trimStartSide, trimEndSide);
    setIsTrimmingSide(false);
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const handleProcessClick = async () => {
    setIsProcessing(true);
    try {
      await onProcess();
    } finally {
      setIsProcessing(false);
    }
  };

  const needsFront = requirements.front;
  const needsSide = requirements.side;
  const frontReady = !needsFront || videoData.frontVideo?.status === "ready";
  const sideReady = !needsSide || videoData.sideVideo?.status === "ready";
  const isAllRequiredViewsReady = !!frontReady && !!sideReady;

  const getStatusColor = (status?: string) => {
    if (!status) return "bg-muted-foreground/30";
    switch (status) {
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

  const getStatusText = (status?: string) => {
    if (!status) return "Not uploaded";
    switch (status) {
      case "empty":
        return "Not uploaded";
      case "uploading":
        return "Uploading...";
      case "uploaded":
        return "Uploaded - Trim Required";
      case "trimming":
        return "Trimming...";
      case "ready":
        return "Ready";
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

  const VideoUploadArea = ({ 
    side, 
    label, 
    fileInputRef 
  }: { 
    side: "front" | "side"; 
    label: string;
    fileInputRef: React.RefObject<HTMLInputElement>;
  }) => {
    const frontData = videoData.frontVideo;
    const sideData = videoData.sideVideo;
    const status = side === "front" ? frontData?.status : sideData?.status;
    const isRequired = side === "front" ? requirements.front : requirements.side;
    const inputId = side === "front" ? `video-input-front-${exercise.id}` : `video-input-side-${exercise.id}`;

    if (!isRequired) return null;

    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label htmlFor={inputId} className="text-sm font-medium text-foreground cursor-pointer">
            {label}
            {isRequired && <span className="text-red-500 ml-1">*</span>}
          </label>
          <div className="flex items-center gap-2">
            <div className={cn("w-2 h-2 rounded-full", getStatusColor(status))} />
            <span className="text-xs text-muted-foreground">{getStatusText(status)}</span>
          </div>
        </div>

        {status === "empty" && (
          <div
            className="border-2 border-dashed border-border rounded-lg p-6 text-center cursor-pointer hover:border-primary/50 transition-colors"
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="w-8 h-8 mx-auto text-muted-foreground mb-2" />
            <p className="text-sm font-medium text-foreground mb-1">
              Click to upload {side} video
            </p>
            <p className="text-xs text-muted-foreground">
              MP4, MOV (Max 500MB)
            </p>
            <input
              id={inputId}
              ref={fileInputRef}
              type="file"
              accept="video/mp4,video/quicktime,.mov,.mp4"
              className="hidden"
              onChange={(e) => handleFileChange(e, side)}
            />
          </div>
        )}

        {status === "uploading" && (
          <div className="flex items-center justify-center p-6 bg-muted/50 rounded-lg">
            <Loader2 className="w-5 h-5 text-primary animate-spin mr-2" />
            <p className="text-sm text-muted-foreground">Uploading...</p>
          </div>
        )}

        {(status === "uploaded" || status === "ready") && (
          <div className="space-y-3">
            <div className="relative aspect-video bg-black rounded-lg overflow-hidden">
              <video
                ref={side === "front" ? videoRefFront : videoRefSide}
                src={side === "front" ? videoData.frontVideo?.videoUrl : videoData.sideVideo?.videoUrl}
                className="w-full h-full object-contain"
                onLoadedMetadata={side === "front" ? handleVideoLoadFront : handleVideoLoadSide}
                onTimeUpdate={side === "front" ? handleTimeUpdateFront : handleTimeUpdateSide}
                onEnded={() => side === "front" ? setIsPlayingFront(false) : setIsPlayingSide(false)}
              />
              <Button
                size="icon"
                variant="secondary"
                className="absolute bottom-3 left-3"
                onClick={side === "front" ? togglePlayFront : togglePlaySide}
              >
                {(side === "front" ? isPlayingFront : isPlayingSide) ? 
                  <Pause className="w-4 h-4" /> : 
                  <Play className="w-4 h-4" />}
              </Button>
              <div className="absolute bottom-3 right-3 bg-black/70 text-white text-xs px-2 py-1 rounded">
                {formatTime(side === "front" ? currentTimeFront : currentTimeSide)} / {formatTime(side === "front" ? durationFront : durationSide)}
              </div>
            </div>

            {(side === "front" ? isTrimmingFront : isTrimmingSide) ? (
              <div className="space-y-3 p-3 bg-muted/50 rounded-lg">
                <div className="flex items-center gap-2 text-sm">
                  <Scissors className="w-4 h-4 text-primary" />
                  <span className="font-medium">Trim {label}</span>
                </div>
                <Slider
                  value={[side === "front" ? trimStartFront : trimStartSide, side === "front" ? trimEndFront : trimEndSide]}
                  min={0}
                  max={(side === "front" ? durationFront : durationSide) || 100}
                  step={0.1}
                  onValueChange={side === "front" ? handleTrimChangeFront : handleTrimChangeSide}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Start: {formatTime(side === "front" ? trimStartFront : trimStartSide)}</span>
                  <span>Duration: {formatTime((side === "front" ? trimEndFront - trimStartFront : trimEndSide - trimStartSide))}</span>
                  <span>End: {formatTime(side === "front" ? trimEndFront : trimEndSide)}</span>
                </div>
                <div className="flex gap-2">
                  <Button 
                    size="sm" 
                    onClick={side === "front" ? saveTrimFront : saveTrimSide}
                  >
                    <Check className="w-4 h-4 mr-1" />
                    Save
                  </Button>
                  <Button 
                    size="sm" 
                    variant="outline" 
                    onClick={() => side === "front" ? setIsTrimmingFront(false) : setIsTrimmingSide(false)}
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
                  onClick={() => side === "front" ? setIsTrimmingFront(true) : setIsTrimmingSide(true)}
                >
                  <Scissors className="w-4 h-4 mr-1" />
                  Trim
                </Button>
                <Button 
                  size="sm" 
                  variant="outline" 
                  onClick={() => fileInputRef.current?.click()}
                >
                  <RotateCcw className="w-4 h-4 mr-1" />
                  Replace
                </Button>
                <Button 
                  size="sm" 
                  variant="outline" 
                  onClick={() => onRemove(side)}
                >
                  <X className="w-4 h-4 mr-1" />
                  Remove
                </Button>
                <input                  id={inputId}                  ref={fileInputRef}
                  type="file"
                  accept="video/mp4,video/quicktime,.mov,.mp4"
                  className="hidden"
                  onChange={(e) => handleFileChange(e, side)}
                />
              </div>
            )}

            {status === "ready" && (
              <div className="flex items-center gap-2 p-2 bg-green-500/10 rounded-lg border border-green-500/20">
                <Check className="w-4 h-4 text-green-600" />
                <span className="text-xs text-green-700 dark:text-green-400">
                  Video is ready
                </span>
              </div>
            )}
          </div>
        )}

        {status === "error" && (
          <div className="flex flex-col items-center justify-center p-6 bg-destructive/10 rounded-lg border border-destructive/20">
            <AlertCircle className="w-6 h-6 text-destructive mb-2" />
            <p className="text-sm text-destructive">An error occurred</p>
            {videoData.result?.interpretation && (
              <p className="text-xs text-muted-foreground mt-1 text-center max-w-sm">{videoData.result.interpretation}</p>
            )}
            <Button 
              size="sm" 
              variant="outline" 
              className="mt-2" 
              onClick={() => fileInputRef.current?.click()}
            >
              Try Again
            </Button>
            <input
              id={inputId}
              ref={fileInputRef}
              type="file"
              accept="video/mp4,video/quicktime,.mov,.mp4"
              className="hidden"
              onChange={(e) => handleFileChange(e, side)}
            />
          </div>
        )}
      </div>
    );
  };

  return (
    <Card className="overflow-hidden">
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
        </div>
      </div>

      <div className="p-4 space-y-6">
        <VideoUploadArea 
          side="front" 
          label={requirements.frontLabel || "Front Video"}
          fileInputRef={fileInputFrontRef}
        />
        
        <VideoUploadArea 
          side="side" 
          label={requirements.sideLabel || "Side Video"}
          fileInputRef={fileInputSideRef}
        />

        {isAllRequiredViewsReady && (
          <div className="pt-2 border-t border-border">
            <Button 
              className="w-full"
              onClick={handleProcessClick}
              disabled={isProcessing}
            >
              {isProcessing && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              {isProcessing ? "Processing Exercise..." : "Process Exercise"}
            </Button>
          </div>
        )}

        {videoData.status === "completed" && videoData.result && (
          <div className="p-4 bg-green-500/10 rounded-lg border border-green-500/20 space-y-3">
            <div className="flex items-center gap-2">
              <Check className="w-4 h-4 text-green-600" />
              <span className="text-sm font-medium text-green-700 dark:text-green-400">
                Analysis Complete
              </span>
            </div>
            
            {/* View warnings */}
            {videoData.result.rawMetrics?.view_warnings && 
              (videoData.result.rawMetrics.view_warnings as string[]).length > 0 && (
              <div className="p-3 bg-yellow-500/20 rounded-lg border border-yellow-500/30">
                <div className="flex items-center gap-2 mb-2">
                  <AlertCircle className="w-4 h-4 text-yellow-600" />
                  <span className="text-sm font-medium text-yellow-700 dark:text-yellow-400">
                    View Detection Warning
                  </span>
                </div>
                <ul className="text-xs text-yellow-700 dark:text-yellow-300 space-y-1">
                  {(videoData.result.rawMetrics.view_warnings as string[]).map((warning, idx) => (
                    <li key={idx}>{warning}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Always show score - even if 0 */}
            <div className="text-sm text-foreground">
              <p className="font-medium">
                Score: {videoData.result.totalScore ?? 'N/A'}/{videoData.result.maxScore ?? 'N/A'}
              </p>
              {videoData.result.interpretation && (
                <p className="text-xs text-muted-foreground mt-1">
                  {videoData.result.interpretation}
                </p>
              )}
            </div>

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
    </Card>
  );
}

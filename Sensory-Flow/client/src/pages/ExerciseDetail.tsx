import { Activity, ArrowLeft, Home } from "lucide-react";
import { Link } from "wouter";

import { useAssessment } from "@/context/AssessmentContext";
import { exerciseTypes, exerciseVideoRequirements } from "@shared/schema";
import { DualVideoExerciseCard } from "@/components/DualVideoExerciseCard";
import { ExerciseCard } from "@/components/ExerciseCard";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type ExerciseDetailProps = {
  params: {
    exerciseId: string;
  };
};

export default function ExerciseDetail({ params }: ExerciseDetailProps) {
  const { exerciseId } = params;
  const {
    exercises,
    updateExercise,
    ageGroup,
    setCurrentStep,
    assessmentId,
  } = useAssessment();

  const exerciseType = exerciseTypes.find((ex) => ex.id === exerciseId);
  const videoData = exercises.find((ex) => ex.exerciseId === exerciseId);
  const requirements = exerciseVideoRequirements[exerciseId] || {
    front: false,
    side: false,
  };

  if (!exerciseType || !videoData) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-lg font-medium text-foreground">
            Exercise not found.
          </p>
          <Link href="/assessment">
            <Button variant="outline">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Assessment
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  const handleUploadFront = (file: File) => {
    const videoUrl = URL.createObjectURL(file);
    updateExercise(exerciseId, {
      frontVideo: {
        videoFile: file,
        videoUrl,
        status: "ready",
      },
    });
  };

  const handleUploadSide = (file: File) => {
    const videoUrl = URL.createObjectURL(file);
    updateExercise(exerciseId, {
      sideVideo: {
        videoFile: file,
        videoUrl,
        status: "ready",
      },
    });
  };

  const handleTrimSave = (
    side: "front" | "side",
    start: number,
    end: number,
  ) => {
    const current = exercises.find((ex) => ex.exerciseId === exerciseId);
    if (!current) return;

    if (side === "front" && current.frontVideo) {
      updateExercise(exerciseId, {
        frontVideo: {
          ...current.frontVideo,
          trimStart: start,
          trimEnd: end,
          status: "ready",
        },
      });
    } else if (side === "side" && current.sideVideo) {
      updateExercise(exerciseId, {
        sideVideo: {
          ...current.sideVideo,
          trimStart: start,
          trimEnd: end,
          status: "ready",
        },
      });
    }
  };

  const handleRemove = (side: "front" | "side") => {
    const current = exercises.find((ex) => ex.exerciseId === exerciseId);
    if (!current) return;

    if (side === "front" && current.frontVideo?.videoUrl) {
      URL.revokeObjectURL(current.frontVideo.videoUrl);
      updateExercise(exerciseId, {
        frontVideo: {
          status: "empty",
        },
      });
    } else if (side === "side" && current.sideVideo?.videoUrl) {
      URL.revokeObjectURL(current.sideVideo.videoUrl);
      updateExercise(exerciseId, {
        sideVideo: {
          status: "empty",
        },
      });
    }
  };

  const handleProcessExercise = async () => {
    const current = exercises.find((ex) => ex.exerciseId === exerciseId);
    if (!current) return;

    updateExercise(exerciseId, { status: "processing" });

    try {
      const formData = new FormData();
      formData.append("exerciseId", exerciseId);
      formData.append("ageGroup", ageGroup || "7 years");

      if (assessmentId != null) {
        formData.append("assessmentId", String(assessmentId));
      }

      if (current.frontVideo?.videoFile) {
        formData.append("frontVideo", current.frontVideo.videoFile);
      }
      if (current.sideVideo?.videoFile) {
        formData.append("sideVideo", current.sideVideo.videoFile);
      }

      const response = await fetch("/api/process-exercise", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Processing failed: ${response.statusText}`);
      }

      const result = (await response.json()) as Record<string, any>;
      const success = result.success !== false;

      if (!success && result.error) {
        console.error("Processing failed:", result.error);
      }

      updateExercise(exerciseId, {
        status: success ? "completed" : "error",
        result: {
          rawMetrics: (result.rawMetrics as Record<string, unknown>) || {},
          scores: (result.scores as Record<string, number>) || {},
          totalScore: (result.totalScore as number) ?? 0,
          maxScore: (result.maxScore as number) ?? 0,
          interpretation: (result.interpretation as string) || (result.error as string) || "Processing failed",
        },
      });
    } catch (error) {
      console.error("Error processing exercise:", error);
      const isConnectionError = error instanceof TypeError && (error as TypeError).message === "Failed to fetch";
      if (isConnectionError) {
        alert(
          "Cannot connect to the server. Please ensure:\n\n" +
          "1. The development server is running: npm run dev\n" +
          "2. The FastAPI backend is running on port 8000 (for video processing)\n\n" +
          "Then try again."
        );
      }
      updateExercise(exerciseId, {
        status: "error",
      });
    }
  };

  const handleBack = () => {
    setCurrentStep(7);
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link href="/">
              <div
                className="flex items-center gap-3 cursor-pointer"
                data-testid="link-logo"
              >
                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary text-primary-foreground">
                  <Activity className="w-6 h-6" />
                </div>
                <div className="hidden sm:block">
                  <h1 className="text-xl font-semibold text-foreground">
                    SensoryAssess Pro
                  </h1>
                  <p className="text-xs text-muted-foreground">
                    Exercise: {exerciseType.name}
                  </p>
                </div>
              </div>
            </Link>
          </div>
          <Link href="/assessment">
            <Button
              variant="outline"
              size="sm"
              onClick={handleBack}
              data-testid="button-back-assessment"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Assessment
            </Button>
          </Link>
        </div>
      </header>

      <main className="py-8 px-4">
        <div className={cn("mx-auto max-w-4xl space-y-6")}>
          <div>
            <h2 className="text-2xl font-bold text-foreground mb-1">
              {exerciseType.name}
            </h2>
            <p className="text-muted-foreground mb-2">
              {exerciseType.description}
            </p>
            <p className="text-xs text-muted-foreground">
              Upload the required views for this exercise, trim if needed, and
              then run automated scoring.
            </p>
          </div>

          <DualVideoExerciseCard
            exercise={exerciseType}
            videoData={videoData}
            onUploadFront={handleUploadFront}
            onUploadSide={handleUploadSide}
            onTrimSave={handleTrimSave}
            onRemove={handleRemove}
            onProcess={handleProcessExercise}
          />
        </div>
      </main>
    </div>
  );
}


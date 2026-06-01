import { useState } from "react";
import { Activity, Home, ArrowLeft, ArrowRight, Loader2, Download, RefreshCw, CheckCircle2, Clock, XCircle, Upload, Video, Scissors, Check, X, Play, Pause, RotateCcw, AlertCircle } from "lucide-react";
import { Link, useLocation } from "wouter";

import { useAssessment } from "@/context/AssessmentContext";
import { StepIndicator } from "@/components/StepIndicator";
import { DemographicForm } from "@/components/forms/DemographicForm";
import { BirthMedicalForm } from "@/components/forms/BirthMedicalForm";
import { PhysicalParametersForm } from "@/components/forms/PhysicalParametersForm";
import { EducationalInfoForm } from "@/components/forms/EducationalInfoForm";
import { CaregiverInfoForm } from "@/components/forms/CaregiverInfoForm";
import { TherapistInfoForm } from "@/components/forms/TherapistInfoForm";
import { AgeGroupSelection } from "@/components/forms/AgeGroupSelection";
import { ExerciseCard } from "@/components/ExerciseCard";
import { DualVideoExerciseCard } from "@/components/DualVideoExerciseCard";
import { downloadReport } from "@/components/ReportGenerator";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { exerciseTypes, exerciseVideoRequirements } from "@shared/schema";
import { cn } from "@/lib/utils";

function ExerciseUploadStep() {
  const { exercises, updateExercise, setCurrentStep, currentStep, ageGroup } = useAssessment();
  const [isProcessing, setIsProcessing] = useState(false);

  const handleUploadFront = async (exerciseId: string, file: File) => {
    const videoData = exercises.find(ex => ex.exerciseId === exerciseId);
    if (!videoData) return;
    
    const videoUrl = URL.createObjectURL(file);
    updateExercise(exerciseId, {
      status: "ready",
      result: undefined,
      frontVideo: {
        videoFile: file,
        videoUrl,
        status: "ready"
      }
    });
  };

  const handleUploadSide = async (exerciseId: string, file: File) => {
    const videoData = exercises.find(ex => ex.exerciseId === exerciseId);
    if (!videoData) return;
    
    const videoUrl = URL.createObjectURL(file);
    updateExercise(exerciseId, {
      status: "ready",
      result: undefined,
      sideVideo: {
        videoFile: file,
        videoUrl,
        status: "ready"
      }
    });
  };

  const handleTrimSave = (exerciseId: string, side: "front" | "side", start: number, end: number) => {
    const videoData = exercises.find(ex => ex.exerciseId === exerciseId);
    if (!videoData) return;
    
    if (side === "front" && videoData.frontVideo) {
      updateExercise(exerciseId, {
        status: "ready",
        result: undefined,
        frontVideo: {
          ...videoData.frontVideo,
          trimStart: start,
          trimEnd: end,
          status: "ready"
        }
      });
    } else if (side === "side" && videoData.sideVideo) {
      updateExercise(exerciseId, {
        status: "ready",
        result: undefined,
        sideVideo: {
          ...videoData.sideVideo,
          trimStart: start,
          trimEnd: end,
          status: "ready"
        }
      });
    }
  };

  const handleRemove = (exerciseId: string, side: "front" | "side") => {
    const videoData = exercises.find(ex => ex.exerciseId === exerciseId);
    if (!videoData) return;
    
    if (side === "front" && videoData.frontVideo?.videoUrl) {
      URL.revokeObjectURL(videoData.frontVideo.videoUrl);
      updateExercise(exerciseId, {
        status: "empty",
        result: undefined,
        frontVideo: {
          status: "empty"
        }
      });
    } else if (side === "side" && videoData.sideVideo?.videoUrl) {
      URL.revokeObjectURL(videoData.sideVideo.videoUrl);
      updateExercise(exerciseId, {
        status: "empty",
        result: undefined,
        sideVideo: {
          status: "empty"
        }
      });
    }
  };

  const handleProcessExercise = async (exerciseId: string) => {
    const videoData = exercises.find(ex => ex.exerciseId === exerciseId);
    if (!videoData) return;

    updateExercise(exerciseId, { status: "processing" });
    setIsProcessing(true);

    try {
      const formData = new FormData();
      formData.append("exerciseId", exerciseId);
      formData.append("ageGroup", ageGroup || "7 years");
      
      if (videoData.frontVideo?.videoFile) {
        formData.append("frontVideo", videoData.frontVideo.videoFile);
      }
      if (videoData.sideVideo?.videoFile) {
        formData.append("sideVideo", videoData.sideVideo.videoFile);
      }

      const response = await fetch("/api/process-exercise", {
        method: "POST",
        body: formData
      });

      if (!response.ok) {
        throw new Error(`Processing failed: ${response.statusText}`);
      }

      const result = await response.json() as Record<string, unknown>;
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
        status: "error"
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleObservationChange = (exerciseId: string, value: string) => {
    updateExercise(exerciseId, { additionalObservation: value });
  };

  const handleBack = () => {
    setCurrentStep(6);
  };

  const handleProceedToResults = async () => {
    const completedExercises = exercises.filter(ex => ex.status === "completed");
    
    if (completedExercises.length === 0) {
      alert("Please upload and process at least one exercise before proceeding.");
      return;
    }

    setCurrentStep(8);
  };

  const uploadedCount = exercises.filter(ex => 
    ex.status !== "empty" && ex.status !== "error"
  ).length;

  const completedCount = exercises.filter(ex => 
    ex.status === "completed"
  ).length;

  return (
    <div className="space-y-8">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-foreground mb-2">Upload Exercise Videos</h2>
        <p className="text-muted-foreground">
          Upload videos for each exercise you want to assess. Some exercises require both front and side views.
        </p>
        <div className="flex items-center gap-4 mt-4 text-sm">
          <span className="text-muted-foreground" data-testid="text-uploaded-count">
            In Progress: <span className="font-semibold text-foreground">{uploadedCount}/9</span>
          </span>
          <span className="text-muted-foreground" data-testid="text-ready-count">
            Completed: <span className="font-semibold text-primary">{completedCount}/9</span>
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {exerciseTypes.map((exercise) => {
          const videoData = exercises.find(ex => ex.exerciseId === exercise.id);
          const requirements = exerciseVideoRequirements[exercise.id] || { front: false, side: false };
          
          if (!videoData) return null;

          // Use DualVideoExerciseCard for exercises that need multiple views
          const needsDualVideo = (requirements.front || requirements.side) && 
                                (Object.keys(requirements).filter(k => requirements[k as keyof typeof requirements]).length > 1);
          
          const card =
            needsDualVideo ||
            exercise.id.startsWith("one_leg") ||
            exercise.id.startsWith("tandem_walking") ||
            exercise.id === "jumping_jacks" ? (
              <DualVideoExerciseCard
                key={exercise.id}
                exercise={exercise}
                videoData={videoData}
                onUploadFront={(file) => handleUploadFront(exercise.id, file)}
                onUploadSide={(file) => handleUploadSide(exercise.id, file)}
                onTrimSave={(side, start, end) =>
                  handleTrimSave(exercise.id, side, start, end)
                }
                onRemove={(side) => handleRemove(exercise.id, side)}
                onProcess={() => handleProcessExercise(exercise.id)}
                observation={videoData.additionalObservation}
                onObservationChange={(val) => handleObservationChange(exercise.id, val)}
              />
            ) : (
              <ExerciseCard
                key={exercise.id}
                exercise={exercise}
                videoData={videoData}
                onUpload={(file) => handleUploadFront(exercise.id, file)}
                onTrimSave={(start, end) =>
                  handleTrimSave(exercise.id, "front", start, end)
                }
                onRemove={() => handleRemove(exercise.id, "front")}
                observation={videoData.additionalObservation}
                onObservationChange={(val) => handleObservationChange(exercise.id, val)}
              />
            );

          return (
            <div key={exercise.id} className="space-y-2">
              {card}
              <div className="flex justify-end">
                <Link href={`/assessment/exercise/${exercise.id}`}>
                  <Button variant="outline" size="sm">
                    Open exercise page
                  </Button>
                </Link>
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex items-center justify-between gap-4 pt-6 border-t border-border">
        <Button
          variant="outline"
          onClick={handleBack}
          disabled={isProcessing}
          data-testid="button-back-exercises"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>
        <Button
          onClick={handleProceedToResults}
          disabled={completedCount === 0 || isProcessing}
          data-testid="button-proceed-results"
        >
          Proceed to Results
          <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );
}

function ResultsStep() {
  const { 
    getFullAssessment, 
    exercises, 
    demographic, 
    ageGroup, 
    resetAssessment, 
    setCurrentStep,
    saveAssessment,
    updateAssessmentOnServer,
    assessmentId,
    isSaving,
    saveError
  } = useAssessment();
  const [, setLocation] = useLocation();
  const [hasSaved, setHasSaved] = useState(false);
  const [localSaveError, setLocalSaveError] = useState<string | null>(null);

  const handleSaveAssessment = async () => {
    setHasSaved(false);
    setLocalSaveError(null);
    try {
      if (assessmentId) {
        await updateAssessmentOnServer();
      } else {
        await saveAssessment();
      }
      setHasSaved(true);
    } catch (error) {
      setHasSaved(false);
      setLocalSaveError(error instanceof Error ? error.message : "Failed to save assessment");
    }
  };

  const handleDownloadReport = () => {
    const assessment = getFullAssessment();
    downloadReport(assessment);
  };

  const handleStartNew = () => {
    resetAssessment();
    setLocation("/");
  };

  const handleBack = () => {
    setCurrentStep(7);
  };

  const completedExercises = exercises.filter(ex => ex.status === "completed");
  const isStandardAgeGroup = ageGroup?.includes("6 years") || ageGroup?.includes("7 years");

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle2 className="w-4 h-4 text-green-600" />;
      case "processing":
      case "ready":
        return <Clock className="w-4 h-4 text-yellow-600" />;
      case "error":
        return <XCircle className="w-4 h-4 text-red-600" />;
      default:
        return null;
    }
  };

  const getScoreColor = (score?: number, maxScore?: number) => {
    if (score === undefined || maxScore === undefined) return "bg-muted text-muted-foreground";
    const percentage = (score / maxScore) * 100;
    if (percentage >= 80) return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
    if (percentage >= 60) return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200";
    if (percentage >= 40) return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200";
    return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Assessment Results</h2>
          <p className="text-muted-foreground">
            Review the assessment results and download the report
          </p>
        </div>
        <Button 
          size="lg"
          onClick={handleDownloadReport}
          data-testid="button-download-pdf"
        >
          <Download className="w-5 h-5 mr-2" />
          Download PDF Report
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Patient Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Child's Name</p>
              <p className="font-medium text-foreground" data-testid="text-child-name">{demographic.childName || "N/A"}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Age</p>
              <p className="font-medium text-foreground" data-testid="text-child-age">{demographic.calculatedAge || "N/A"}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Age Group</p>
              <p className="font-medium text-foreground" data-testid="text-age-group">{ageGroup || "N/A"}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Assessment Date</p>
              <p className="font-medium text-foreground" data-testid="text-assessment-date">{demographic.dateOfAssessment || "N/A"}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center justify-between gap-4 flex-wrap">
            <span>Exercise Results</span>
            <Badge variant="secondary">
              {completedExercises.length} of {exercises.filter(ex => ex.status !== "empty").length} completed
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {completedExercises.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Clock className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No exercises have been completed yet.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {exercises
                .filter(ex => ex.status === "completed")
                .map((exercise) => {
                  const exerciseInfo = exerciseTypes.find(e => e.id === exercise.exerciseId);
                  
                  return (
                    <div 
                      key={exercise.exerciseId}
                      className="flex flex-col gap-3 p-4 rounded-lg border border-border bg-card"
                      data-testid={`result-${exercise.exerciseId}`}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-3 min-w-0">
                          {getStatusIcon(exercise.status)}
                          <div className="min-w-0">
                            <p className="font-medium text-foreground truncate">
                              {exerciseInfo?.name || exercise.exerciseId}
                            </p>
                          </div>
                        </div>
                        {exercise.result?.totalScore !== undefined && exercise.result?.maxScore && (
                          <div className="flex-shrink-0">
                            <span className={cn(
                              "inline-flex items-center justify-center px-3 py-1 rounded-full text-sm font-semibold",
                              getScoreColor(exercise.result.totalScore, exercise.result.maxScore)
                            )}>
                              {exercise.result.totalScore}/{exercise.result.maxScore}
                            </span>
                          </div>
                        )}
                      </div>
                      {exercise.result?.interpretation && (
                        <p className="text-xs text-muted-foreground">
                          {exercise.result.interpretation}
                        </p>
                      )}
                      {exercise.result?.scores && Object.keys(exercise.result.scores).length > 0 && (
                        <div className="text-xs text-muted-foreground space-y-1 pl-6">
                          {Object.entries(exercise.result.scores).map(([metric, score]) => (
                            <p key={metric}>{metric}: {score}</p>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
            </div>
          )}
        </CardContent>
      </Card>

      {isStandardAgeGroup && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Scoring Guide</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="flex items-center gap-2">
                <span className={cn("w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold", getScoreColor(0))}>0</span>
                <span className="text-sm text-muted-foreground">Below Expected</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={cn("w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold", getScoreColor(1))}>1</span>
                <span className="text-sm text-muted-foreground">Emerging</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={cn("w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold", getScoreColor(2))}>2</span>
                <span className="text-sm text-muted-foreground">Developing</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={cn("w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold", getScoreColor(3))}>3</span>
                <span className="text-sm text-muted-foreground">Age Appropriate</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {(localSaveError || saveError) && (
        <div className="p-4 bg-red-50 dark:bg-red-950 rounded-lg border border-red-200 dark:border-red-800 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-700 dark:text-red-300" data-testid="text-save-error">
            {localSaveError || saveError}
          </p>
        </div>
      )}

      {hasSaved && !localSaveError && !saveError && (
        <div className="p-4 bg-green-50 dark:bg-green-950 rounded-lg border border-green-200 dark:border-green-800 flex items-center gap-3">
          <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0" />
          <p className="text-sm text-green-700 dark:text-green-300" data-testid="text-save-success">
            Assessment saved successfully! {assessmentId && `(ID: ${assessmentId})`}
          </p>
        </div>
      )}

      <div className="flex items-center justify-between gap-4 pt-6 border-t border-border flex-wrap">
        <Button
          variant="outline"
          onClick={handleBack}
          data-testid="button-back-results"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Exercises
        </Button>

        <div className="flex items-center gap-2 flex-wrap">
          <Button
            variant="outline"
            onClick={handleSaveAssessment}
            disabled={isSaving}
            data-testid="button-save-assessment"
          >
            {isSaving ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : hasSaved ? (
              <>
                <CheckCircle2 className="w-4 h-4 mr-2" />
                Saved
              </>
            ) : (
              <>
                <Upload className="w-4 h-4 mr-2" />
                Save Assessment
              </>
            )}
          </Button>

          <Button
            variant="outline"
            onClick={handleStartNew}
            data-testid="button-new-assessment"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Start New Assessment
          </Button>

          <Button
            onClick={handleDownloadReport}
            data-testid="button-download-final"
          >
            <Download className="w-4 h-4 mr-2" />
            Download PDF Report
          </Button>
        </div>
      </div>

      <div className="p-4 bg-muted/50 rounded-lg border border-border text-center">
        <p className="text-sm text-muted-foreground italic">
          This document is auto-generated and does not require a signature.
        </p>
      </div>
    </div>
  );
}

export default function Assessment() {
  const { currentStep } = useAssessment();

  const renderCurrentStep = () => {
    switch (currentStep) {
      case 0:
        return <DemographicForm />;
      case 1:
        return <BirthMedicalForm />;
      case 2:
        return <PhysicalParametersForm />;
      case 3:
        return <EducationalInfoForm />;
      case 4:
        return <CaregiverInfoForm />;
      case 5:
        return <TherapistInfoForm />;
      case 6:
        return <AgeGroupSelection />;
      case 7:
        return <ExerciseUploadStep />;
      case 8:
        return <ResultsStep />;
      default:
        return <DemographicForm />;
    }
  };

  const getSubtitle = () => {
    switch (currentStep) {
      case 7:
        return "Exercise Upload";
      case 8:
        return "Assessment Results";
      default:
        return "New Assessment";
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link href="/">
              <div className="flex items-center gap-3 cursor-pointer" data-testid="link-logo">
                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary text-primary-foreground">
                  <Activity className="w-6 h-6" />
                </div>
                <div className="hidden sm:block">
                  <h1 className="text-xl font-semibold text-foreground">SensoryAssess Pro</h1>
                  <p className="text-xs text-muted-foreground">{getSubtitle()}</p>
                </div>
              </div>
            </Link>
          </div>
          <Link href="/">
            <Button variant="outline" size="sm" data-testid="button-home">
              <Home className="w-4 h-4 mr-2" />
              Home
            </Button>
          </Link>
        </div>
      </header>

      <div className="border-b border-border bg-card/50">
        <StepIndicator currentStep={currentStep} />
      </div>

      <main className="py-8 px-4">
        <div className={cn(
          "mx-auto",
          currentStep === 7 ? "max-w-6xl" : "max-w-4xl",
          currentStep === 8 ? "max-w-5xl" : ""
        )}>
          {renderCurrentStep()}
        </div>
      </main>
    </div>
  );
}

import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import type { 
  DemographicData, 
  BirthMedicalData, 
  PhysicalParametersData, 
  EducationalInfoData, 
  CaregiverInfoData, 
  TherapistInfoData,
  ExerciseVideoData,
  AssessmentData,
  SelectAssessment
} from "@shared/schema";
import { exerciseTypes, exerciseVideoRequirements } from "@shared/schema";
import { apiRequest } from "@/lib/queryClient";

interface AssessmentContextType {
  currentStep: number;
  setCurrentStep: (step: number) => void;
  demographic: Partial<DemographicData>;
  setDemographic: (data: Partial<DemographicData>) => void;
  birthMedical: Partial<BirthMedicalData>;
  setBirthMedical: (data: Partial<BirthMedicalData>) => void;
  physicalParameters: Partial<PhysicalParametersData>;
  setPhysicalParameters: (data: Partial<PhysicalParametersData>) => void;
  educationalInfo: Partial<EducationalInfoData>;
  setEducationalInfo: (data: Partial<EducationalInfoData>) => void;
  caregiverInfo: Partial<CaregiverInfoData>;
  setCaregiverInfo: (data: Partial<CaregiverInfoData>) => void;
  therapistInfo: Partial<TherapistInfoData>;
  setTherapistInfo: (data: Partial<TherapistInfoData>) => void;
  ageGroup: string;
  setAgeGroup: (ageGroup: string) => void;
  exercises: ExerciseVideoData[];
  setExercises: (exercises: ExerciseVideoData[]) => void;
  updateExercise: (exerciseId: string, data: Partial<ExerciseVideoData>) => void;
  getFullAssessment: () => Partial<AssessmentData>;
  resetAssessment: () => void;
  assessmentId: number | null;
  setAssessmentId: (id: number | null) => void;
  saveAssessment: () => Promise<number>;
  loadAssessment: (id: number) => Promise<void>;
  updateAssessmentOnServer: () => Promise<void>;
  isSaving: boolean;
  isLoading: boolean;
  saveError: string | null;
  loadError: string | null;
}

const AssessmentContext = createContext<AssessmentContextType | undefined>(undefined);

function createInitialExercises(): ExerciseVideoData[] {
  return exerciseTypes.map((ex) => {
    const req = exerciseVideoRequirements[ex.id] || { front: false, side: false };

    return {
      exerciseId: ex.id,
      status: "empty" as const,
      videoFile: undefined,
      videoUrl: undefined,
      trimStart: undefined,
      trimEnd: undefined,
      // For dual‑view exercises, initialize view objects so upload UI appears
      frontVideo: req.front
        ? {
            status: "empty",
            videoFile: undefined,
            videoUrl: undefined,
            trimStart: undefined,
            trimEnd: undefined,
          }
        : undefined,
      sideVideo: req.side
        ? {
            status: "empty",
            videoFile: undefined,
            videoUrl: undefined,
            trimStart: undefined,
            trimEnd: undefined,
          }
        : undefined,
      result: undefined,
    };
  });
}

const initialExercises: ExerciseVideoData[] = createInitialExercises();

export function AssessmentProvider({ children }: { children: ReactNode }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [demographic, setDemographic] = useState<Partial<DemographicData>>({});
  const [birthMedical, setBirthMedical] = useState<Partial<BirthMedicalData>>({});
  const [physicalParameters, setPhysicalParameters] = useState<Partial<PhysicalParametersData>>({});
  const [educationalInfo, setEducationalInfo] = useState<Partial<EducationalInfoData>>({});
  const [caregiverInfo, setCaregiverInfo] = useState<Partial<CaregiverInfoData>>({});
  const [therapistInfo, setTherapistInfo] = useState<Partial<TherapistInfoData>>({});
  const [ageGroup, setAgeGroup] = useState<string>("");
  const [exercises, setExercises] = useState<ExerciseVideoData[]>(initialExercises);
  const [assessmentId, setAssessmentId] = useState<number | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const updateExercise = useCallback((exerciseId: string, data: Partial<ExerciseVideoData>) => {
    setExercises(prev => prev.map(ex => 
      ex.exerciseId === exerciseId ? { ...ex, ...data } : ex
    ));
  }, []);

  const getFullAssessment = useCallback((): Partial<AssessmentData> => {
    return {
      demographic: demographic as DemographicData,
      birthMedical: birthMedical as BirthMedicalData,
      physicalParameters: physicalParameters as PhysicalParametersData,
      educationalInfo: educationalInfo as EducationalInfoData,
      caregiverInfo: caregiverInfo as CaregiverInfoData,
      therapistInfo: therapistInfo as TherapistInfoData,
      ageGroup,
      exercises,
      status: "in_progress"
    };
  }, [demographic, birthMedical, physicalParameters, educationalInfo, caregiverInfo, therapistInfo, ageGroup, exercises]);

  const resetAssessment = useCallback(() => {
    setCurrentStep(0);
    setDemographic({});
    setBirthMedical({});
    setPhysicalParameters({});
    setEducationalInfo({});
    setCaregiverInfo({});
    setTherapistInfo({});
    setAgeGroup("");
    setExercises(createInitialExercises());
    setAssessmentId(null);
    setSaveError(null);
    setLoadError(null);
  }, []);

  const saveAssessment = useCallback(async (): Promise<number> => {
    setIsSaving(true);
    setSaveError(null);
    
    try {
      const exercisesForSave = exercises.map(ex => ({
        exerciseId: ex.exerciseId,
        status: ex.status,
        videoUrl: ex.videoUrl,
        trimStart: ex.trimStart,
        trimEnd: ex.trimEnd,
        result: ex.result
      }));

      const assessmentData = {
        demographic: demographic as DemographicData,
        birthMedical: birthMedical as BirthMedicalData,
        physicalParameters: physicalParameters as PhysicalParametersData,
        educationalInfo: educationalInfo as EducationalInfoData,
        caregiverInfo: caregiverInfo as CaregiverInfoData,
        therapistInfo: therapistInfo as TherapistInfoData,
        ageGroup,
        exercises: exercisesForSave,
        status: "in_progress"
      };

      const response = await apiRequest("POST", "/api/assessments", assessmentData);
      const saved: SelectAssessment = await response.json();
      setAssessmentId(saved.id);
      return saved.id;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to save assessment";
      setSaveError(message);
      throw error;
    } finally {
      setIsSaving(false);
    }
  }, [demographic, birthMedical, physicalParameters, educationalInfo, caregiverInfo, therapistInfo, ageGroup, exercises]);

  const updateAssessmentOnServer = useCallback(async (): Promise<void> => {
    if (!assessmentId) {
      throw new Error("No assessment ID to update");
    }
    
    setIsSaving(true);
    setSaveError(null);
    
    try {
      const exercisesForSave = exercises.map(ex => ({
        exerciseId: ex.exerciseId,
        status: ex.status,
        videoUrl: ex.videoUrl,
        trimStart: ex.trimStart,
        trimEnd: ex.trimEnd,
        result: ex.result
      }));

      const assessmentData = {
        demographic: demographic as DemographicData,
        birthMedical: birthMedical as BirthMedicalData,
        physicalParameters: physicalParameters as PhysicalParametersData,
        educationalInfo: educationalInfo as EducationalInfoData,
        caregiverInfo: caregiverInfo as CaregiverInfoData,
        therapistInfo: therapistInfo as TherapistInfoData,
        ageGroup,
        exercises: exercisesForSave,
        status: "in_progress"
      };

      await apiRequest("PATCH", `/api/assessments/${assessmentId}`, assessmentData);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to update assessment";
      setSaveError(message);
      throw error;
    } finally {
      setIsSaving(false);
    }
  }, [assessmentId, demographic, birthMedical, physicalParameters, educationalInfo, caregiverInfo, therapistInfo, ageGroup, exercises]);

  const loadAssessment = useCallback(async (id: number): Promise<void> => {
    setIsLoading(true);
    setLoadError(null);
    
    try {
      const response = await fetch(`/api/assessments/${id}`, {
        credentials: "include"
      });
      
      if (!response.ok) {
        throw new Error(`Failed to load assessment: ${response.statusText}`);
      }
      
      const assessment: SelectAssessment = await response.json();
      
      setAssessmentId(assessment.id);
      setDemographic(assessment.demographic || {});
      setBirthMedical(assessment.birthMedical || {});
      setPhysicalParameters(assessment.physicalParameters || {});
      setEducationalInfo(assessment.educationalInfo || {});
      setCaregiverInfo(assessment.caregiverInfo || {});
      setTherapistInfo(assessment.therapistInfo || {});
      setAgeGroup(assessment.ageGroup || "");
      
      if (assessment.exercises && Array.isArray(assessment.exercises)) {
        const loadedExercises = exerciseTypes.map(exType => {
          const savedEx = assessment.exercises.find(e => e.exerciseId === exType.id);
          return savedEx || {
            exerciseId: exType.id,
            status: "empty" as const,
            videoFile: undefined,
            videoUrl: undefined,
            trimStart: undefined,
            trimEnd: undefined,
            result: undefined
          };
        });
        setExercises(loadedExercises);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to load assessment";
      setLoadError(message);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return (
    <AssessmentContext.Provider value={{
      currentStep,
      setCurrentStep,
      demographic,
      setDemographic,
      birthMedical,
      setBirthMedical,
      physicalParameters,
      setPhysicalParameters,
      educationalInfo,
      setEducationalInfo,
      caregiverInfo,
      setCaregiverInfo,
      therapistInfo,
      setTherapistInfo,
      ageGroup,
      setAgeGroup,
      exercises,
      setExercises,
      updateExercise,
      getFullAssessment,
      resetAssessment,
      assessmentId,
      setAssessmentId,
      saveAssessment,
      loadAssessment,
      updateAssessmentOnServer,
      isSaving,
      isLoading,
      saveError,
      loadError
    }}>
      {children}
    </AssessmentContext.Provider>
  );
}

export function useAssessment() {
  const context = useContext(AssessmentContext);
  if (context === undefined) {
    throw new Error("useAssessment must be used within an AssessmentProvider");
  }
  return context;
}

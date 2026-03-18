/**
 * Scoring Algorithm for SensoryAssess Pro
 * 
 * Implements deterministic 0-3 scoring for exercises based on age group.
 * Score meanings:
 *   0 = Below Expected
 *   1 = Emerging
 *   2 = Developing
 *   3 = Age Appropriate
 */

export type AgeGroupKey = "6_years" | "7_years";

export interface ScoringThreshold {
  score3Min: number;
  score2Min: number;
  score1Min: number;
}

export interface ExerciseScoringConfig {
  metric: "duration" | "steps" | "count";
  unit: string;
  "6_years": ScoringThreshold;
  "7_years": ScoringThreshold;
}

export const exerciseScoringConfigs: Record<string, ExerciseScoringConfig> = {
  prone_extension: {
    metric: "duration",
    unit: "seconds",
    "6_years": { score3Min: 20, score2Min: 12, score1Min: 6 },
    "7_years": { score3Min: 25, score2Min: 15, score1Min: 8 }
  },
  supine_flexion: {
    metric: "duration",
    unit: "seconds",
    "6_years": { score3Min: 20, score2Min: 12, score1Min: 6 },
    "7_years": { score3Min: 25, score2Min: 15, score1Min: 8 }
  },
  one_leg_right_open: {
    metric: "duration",
    unit: "seconds",
    "6_years": { score3Min: 8, score2Min: 5, score1Min: 2 },
    "7_years": { score3Min: 10, score2Min: 6, score1Min: 3 }
  },
  one_leg_right_close: {
    metric: "duration",
    unit: "seconds",
    "6_years": { score3Min: 4, score2Min: 2, score1Min: 1 },
    "7_years": { score3Min: 6, score2Min: 3, score1Min: 1.5 }
  },
  one_leg_left_open: {
    metric: "duration",
    unit: "seconds",
    "6_years": { score3Min: 8, score2Min: 5, score1Min: 2 },
    "7_years": { score3Min: 10, score2Min: 6, score1Min: 3 }
  },
  one_leg_left_close: {
    metric: "duration",
    unit: "seconds",
    "6_years": { score3Min: 4, score2Min: 2, score1Min: 1 },
    "7_years": { score3Min: 6, score2Min: 3, score1Min: 1.5 }
  },
  tandem_walking_open: {
    metric: "steps",
    unit: "steps",
    "6_years": { score3Min: 8, score2Min: 5, score1Min: 2 },
    "7_years": { score3Min: 10, score2Min: 6, score1Min: 3 }
  },
  tandem_walking_close: {
    metric: "steps",
    unit: "steps",
    "6_years": { score3Min: 5, score2Min: 3, score1Min: 1 },
    "7_years": { score3Min: 7, score2Min: 4, score1Min: 2 }
  },
  jumping_jacks: {
    metric: "count",
    unit: "repetitions",
    "6_years": { score3Min: 8, score2Min: 5, score1Min: 2 },
    "7_years": { score3Min: 10, score2Min: 6, score1Min: 3 }
  }
};

export function getAgeGroupKey(ageGroup: string): AgeGroupKey | null {
  if (ageGroup.includes("6 years")) {
    return "6_years";
  }
  if (ageGroup.includes("7 years")) {
    return "7_years";
  }
  return null;
}

export function calculateExerciseScore(
  exerciseId: string,
  ageGroup: string,
  measuredValue: number
): number {
  const config = exerciseScoringConfigs[exerciseId];
  if (!config) {
    return 0;
  }

  const ageKey = getAgeGroupKey(ageGroup);
  if (!ageKey) {
    return 0;
  }

  const thresholds = config[ageKey];
  
  if (measuredValue >= thresholds.score3Min) {
    return 3;
  }
  if (measuredValue >= thresholds.score2Min) {
    return 2;
  }
  if (measuredValue >= thresholds.score1Min) {
    return 1;
  }
  return 0;
}

export function generateMockMeasuredValue(exerciseId: string): number {
  const config = exerciseScoringConfigs[exerciseId];
  if (!config) {
    return 5;
  }
  
  const maxValue = config["7_years"].score3Min * 1.5;
  const minValue = 0;
  return Math.round((Math.random() * (maxValue - minValue) + minValue) * 10) / 10;
}

export function getExerciseMetricInfo(exerciseId: string): { metric: string; unit: string } {
  const config = exerciseScoringConfigs[exerciseId];
  if (!config) {
    return { metric: "value", unit: "units" };
  }
  return { metric: config.metric, unit: config.unit };
}

export function getScoreLabel(score: number): string {
  switch (score) {
    case 3:
      return "Age Appropriate";
    case 2:
      return "Developing";
    case 1:
      return "Emerging";
    case 0:
    default:
      return "Below Expected";
  }
}

export function getThresholdsForExercise(
  exerciseId: string,
  ageGroup: string
): ScoringThreshold | null {
  const config = exerciseScoringConfigs[exerciseId];
  if (!config) {
    return null;
  }

  const ageKey = getAgeGroupKey(ageGroup);
  if (!ageKey) {
    return null;
  }

  return config[ageKey];
}

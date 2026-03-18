import { pgTable, text, jsonb, timestamp, serial } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const genderOptions = ["Male", "Female", "Others"] as const;
export const yesNoOptions = ["Yes", "No"] as const;
export const educationTypeOptions = ["Mainstream", "Special School"] as const;
export const ageGroupOptions = [
  "6 years 0 months – 6 years 11 months",
  "7 years 0 months – 7 years 11 months",
  "Other age groups"
] as const;

export const exerciseTypes = [
  { id: "prone_extension", name: "Prone Extension", description: "Child lies on stomach and extends limbs" },
  { id: "supine_flexion", name: "Supine Flexion", description: "Child lies on back and flexes limbs" },
  { id: "one_leg_right_open", name: "One Leg Standing (Right leg lift, eyes open)", description: "Balance on left leg, right lifted, eyes open" },
  { id: "one_leg_right_close", name: "One Leg Standing (Right leg lift, eyes close)", description: "Balance on left leg, right lifted, eyes closed" },
  { id: "one_leg_left_open", name: "One Leg Standing (Left leg lift, eyes open)", description: "Balance on right leg, left lifted, eyes open" },
  { id: "one_leg_left_close", name: "One Leg Standing (Left leg lift, eyes close)", description: "Balance on right leg, left lifted, eyes closed" },
  { id: "tandem_walking_open", name: "Tandem Walking (Eyes open)", description: "Heel-to-toe walking with eyes open" },
  { id: "tandem_walking_close", name: "Tandem Walking (Eyes close)", description: "Heel-to-toe walking with eyes closed" },
  { id: "jumping_jacks", name: "Jumping Jacks", description: "Coordinated jumping with arm movements" }
] as const;

export const demographicSchema = z.object({
  childName: z.string().min(1, "Child's name is required"),
  gender: z.enum(genderOptions, { required_error: "Gender is required" }),
  dateOfBirth: z.string().min(1, "Date of birth is required"),
  dateOfAssessment: z.string().min(1, "Date of assessment is required"),
  calculatedAge: z.string().optional()
});

export const birthMedicalSchema = z.object({
  lowBirthWeight: z.enum(yesNoOptions, { required_error: "This field is required" }),
  lowBirthWeightDetails: z.string().optional(),
  premature: z.enum(yesNoOptions, { required_error: "This field is required" }),
  prematureDetails: z.string().optional(),
  birthComplications: z.enum(yesNoOptions, { required_error: "This field is required" }),
  birthComplicationsDetails: z.string().optional(),
  developmentalDisability: z.enum(yesNoOptions, { required_error: "This field is required" }),
  developmentalDisabilityDetails: z.string().optional()
});

export const physicalParametersSchema = z.object({
  height: z.number().min(0.1, "Height is required").max(2.5, "Invalid height"),
  weight: z.number().min(1, "Weight is required").max(200, "Invalid weight"),
  bmi: z.number().optional()
});

export const educationalInfoSchema = z.object({
  enrolledInSchool: z.enum(yesNoOptions, { required_error: "This field is required" }),
  educationType: z.enum(educationTypeOptions).optional(),
  standardClass: z.string().optional(),
  schoolName: z.string().optional()
});

export const caregiverInfoSchema = z.object({
  caregiverName: z.string().optional(),
  relationToChild: z.string().optional(),
  caregiverContact: z.string().optional()
});

export const therapistInfoSchema = z.object({
  therapistName: z.string().min(1, "Therapist name is required"),
  therapistProfession: z.string().min(1, "Profession is required"),
  licenseNumber: z.string().optional(),
  therapistDesignation: z.string().min(1, "Designation is required"),
  serviceProviderDetails: z.string().min(1, "Service provider details are required")
});

// Video view schema for front/side videos
export const videoViewSchema = z.object({
  videoFile: z.any().optional(),
  videoUrl: z.string().optional(),
  trimStart: z.number().optional(),
  trimEnd: z.number().optional(),
  status: z.enum(["empty", "uploading", "uploaded", "trimmed", "ready", "error"]).default("empty")
});

export const exerciseVideoSchema = z.object({
  exerciseId: z.string(),
  // Legacy single video support (for exercises that only need one view)
  videoFile: z.any().optional(),
  videoUrl: z.string().optional(),
  trimStart: z.number().optional(),
  trimEnd: z.number().optional(),
  // New dual video support (front + side views)
  frontVideo: videoViewSchema.optional(),
  sideVideo: videoViewSchema.optional(),
  // Exercise status and results
  status: z.enum(["empty", "uploading", "uploaded", "trimming", "ready", "processing", "completed", "error"]),
  result: z.object({
    values: z.record(z.any()).optional(),
    rawMetrics: z.record(z.any()).optional(),
    scores: z.record(z.number()).optional(),
    totalScore: z.number().optional(),
    maxScore: z.number().optional(),
    interpretation: z.string().optional(),
    score: z.number().optional()
  }).optional()
});

// Define which exercises require which video views
export const exerciseVideoRequirements: Record<string, { front: boolean; side: boolean; frontLabel?: string; sideLabel?: string }> = {
  "prone_extension": { front: false, side: true, sideLabel: "Side View" },
  "supine_flexion": { front: false, side: true, sideLabel: "Side View" },
  "one_leg_right_open": { front: true, side: true, frontLabel: "Front View (ML Sway)", sideLabel: "Side View (AP Sway)" },
  "one_leg_right_close": { front: true, side: true, frontLabel: "Front View (ML Sway)", sideLabel: "Side View (AP Sway)" },
  "one_leg_left_open": { front: true, side: true, frontLabel: "Front View (ML Sway)", sideLabel: "Side View (AP Sway)" },
  "one_leg_left_close": { front: true, side: true, frontLabel: "Front View (ML Sway)", sideLabel: "Side View (AP Sway)" },
  "tandem_walking_open": { front: true, side: true, frontLabel: "Front View (ML Sway)", sideLabel: "Side View (AP Sway)" },
  "tandem_walking_close": { front: true, side: true, frontLabel: "Front View (ML Sway)", sideLabel: "Side View (AP Sway)" },
  "jumping_jacks": { front: true, side: true, frontLabel: "Front View (Required)", sideLabel: "Side View (Required)" }
};

export type VideoViewData = z.infer<typeof videoViewSchema>;

export const assessmentSchema = z.object({
  id: z.string().optional(),
  demographic: demographicSchema,
  birthMedical: birthMedicalSchema,
  physicalParameters: physicalParametersSchema,
  educationalInfo: educationalInfoSchema,
  caregiverInfo: caregiverInfoSchema,
  therapistInfo: therapistInfoSchema,
  ageGroup: z.string(),
  exercises: z.array(exerciseVideoSchema),
  status: z.enum(["draft", "in_progress", "completed"]),
  createdAt: z.string().optional(),
  completedAt: z.string().optional()
});

export type Gender = typeof genderOptions[number];
export type YesNo = typeof yesNoOptions[number];
export type EducationType = typeof educationTypeOptions[number];
export type AgeGroup = typeof ageGroupOptions[number];
export type ExerciseType = typeof exerciseTypes[number];

export type DemographicData = z.infer<typeof demographicSchema>;
export type BirthMedicalData = z.infer<typeof birthMedicalSchema>;
export type PhysicalParametersData = z.infer<typeof physicalParametersSchema>;
export type EducationalInfoData = z.infer<typeof educationalInfoSchema>;
export type CaregiverInfoData = z.infer<typeof caregiverInfoSchema>;
export type TherapistInfoData = z.infer<typeof therapistInfoSchema>;
export type ExerciseVideoData = z.infer<typeof exerciseVideoSchema>;
export type AssessmentData = z.infer<typeof assessmentSchema>;

export type InsertAssessment = Omit<AssessmentData, 'id' | 'createdAt' | 'completedAt'>;

export const assessments = pgTable("assessments", {
  id: serial("id").primaryKey(),
  demographic: jsonb("demographic").notNull().$type<DemographicData>(),
  birthMedical: jsonb("birth_medical").notNull().$type<BirthMedicalData>(),
  physicalParameters: jsonb("physical_parameters").notNull().$type<PhysicalParametersData>(),
  educationalInfo: jsonb("educational_info").notNull().$type<EducationalInfoData>(),
  caregiverInfo: jsonb("caregiver_info").$type<CaregiverInfoData>(),
  therapistInfo: jsonb("therapist_info").notNull().$type<TherapistInfoData>(),
  ageGroup: text("age_group").notNull(),
  exercises: jsonb("exercises").notNull().$type<ExerciseVideoData[]>(),
  status: text("status").notNull().default("draft"),
  createdAt: timestamp("created_at").defaultNow(),
  completedAt: timestamp("completed_at")
});

export const insertAssessmentDBSchema = createInsertSchema(assessments).omit({ 
  id: true, 
  createdAt: true, 
  completedAt: true 
});

export type InsertAssessmentDB = z.infer<typeof insertAssessmentDBSchema>;
export type SelectAssessment = typeof assessments.$inferSelect;

export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  username: text("username").notNull().unique(),
  password: text("password").notNull()
});

export const insertUserSchema = createInsertSchema(users).omit({ id: true });
export type InsertUserDB = z.infer<typeof insertUserSchema>;
export type SelectUser = typeof users.$inferSelect;

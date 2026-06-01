import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import { format } from "date-fns";

import type { AssessmentData, ExerciseVideoData } from "@shared/schema";
import { exerciseTypes } from "@shared/schema";

function toFiniteNumber(v: unknown): number | null {
  if (v == null) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function fmt(v: unknown, decimals = 2): string {
  const n = toFiniteNumber(v);
  if (n == null) return "";
  return n.toFixed(decimals);
}

function inferAgeYears(ageGroup?: string): 6 | 7 | null {
  if (!ageGroup) return null;
  if (ageGroup.includes("6 years")) return 6;
  if (ageGroup.includes("7 years")) return 7;
  return null;
}

function assessmentNorm(ageYears: 6 | 7 | null): { mean: number; sd: number } | null {
  if (ageYears === 6) return { mean: 197, sd: 17 };
  if (ageYears === 7) return { mean: 197, sd: 15 };
  return null;
}

// ---------------------------------------------------------------------------
// Per-exercise parameter definitions: maps exerciseId → list of display rows
// Each row: [displayName, rawMetricKey, scoreKey]
// ---------------------------------------------------------------------------
type ParamDef = [string, string, string];

const EXERCISE_PARAMS: Record<string, ParamDef[]> = {
  prone_extension: [
    ["Neck Extension Angle", "neck_mean_deg", "neck_ext_score"],
    ["Trunk Extension Angle", "trunk_mean_deg", "trunk_ext_score"],
    ["Hip Extension Angle", "hip_mean_deg", "hip_ext_score"],
    ["Knee Extension Angle", "knee_mean_deg", "knee_flex_score"],
    ["Hold Duration", "hold_duration_s", "hold_duration_score"],
  ],
  supine_flexion: [
    ["Neck Flexion Angle", "neck_mean_deg", "neck_flex_score"],
    ["Trunk Flexion Angle", "trunk_mean_deg", "trunk_flex_score"],
    ["Hip Flexion Angle", "hip_mean_deg", "hip_flex_score"],
    ["Knee Flexion Angle", "knee_mean_deg", "knee_flex_score"],
    ["Hold Duration", "hold_duration_s", "hold_duration_score"],
  ],
  one_leg_right_open: [
    ["Mediolateral Sway Mean", "sway_SS_mean", "sway_SS_mean_score"],
    ["Mediolateral Sway Variability", "sway_SS_SD", "sway_SS_SD_score"],
    ["Anteroposterior Sway Mean", "sway_AP_mean", "sway_AP_mean_score"],
    ["Anteroposterior Sway Variability", "sway_AP_SD", "sway_AP_SD_score"],
    ["Toe Touch", "toe_touches", "toe_touches_score"],
  ],
  one_leg_right_close: [
    ["Mediolateral Sway Mean", "sway_SS_mean", "sway_SS_mean_score"],
    ["Mediolateral Sway Variability", "sway_SS_SD", "sway_SS_SD_score"],
    ["Anteroposterior Sway Mean", "sway_AP_mean", "sway_AP_mean_score"],
    ["Anteroposterior Sway Variability", "sway_AP_SD", "sway_AP_SD_score"],
    ["Toe Touch", "toe_touches", "toe_touches_score"],
  ],
  one_leg_left_open: [
    ["Mediolateral Sway Mean", "sway_SS_mean", "sway_SS_mean_score"],
    ["Mediolateral Sway Variability", "sway_SS_SD", "sway_SS_SD_score"],
    ["Anteroposterior Sway Mean", "sway_AP_mean", "sway_AP_mean_score"],
    ["Anteroposterior Sway Variability", "sway_AP_SD", "sway_AP_SD_score"],
    ["Toe Touch", "toe_touches", "toe_touches_score"],
  ],
  one_leg_left_close: [
    ["Mediolateral Sway Mean", "sway_SS_mean", "sway_SS_mean_score"],
    ["Mediolateral Sway Variability", "sway_SS_SD", "sway_SS_SD_score"],
    ["Anteroposterior Sway Mean", "sway_AP_mean", "sway_AP_mean_score"],
    ["Anteroposterior Sway Variability", "sway_AP_SD", "sway_AP_SD_score"],
    ["Toe Touch", "toe_touches", "toe_touches_score"],
  ],
  tandem_walking_open: [
    ["Mediolateral Sway Mean", "ml_sway_mean_deg", "ml_sway_mean_score"],
    ["Mediolateral Sway Variability", "ml_sway_sd_deg", "ml_sway_sd_score"],
    ["Anteroposterior Sway Mean", "ap_sway_mean_deg", "ap_sway_mean_score"],
    ["Anteroposterior Sway Variability", "ap_sway_sd_deg", "ap_sway_sd_score"],
    ["Step Gap (cm)", "mean_step_gap_cm", "step_gap_score"],
  ],
  tandem_walking_close: [
    ["Mediolateral Sway Mean", "ml_sway_mean_deg", "ml_sway_mean_score"],
    ["Mediolateral Sway Variability", "ml_sway_sd_deg", "ml_sway_sd_score"],
    ["Anteroposterior Sway Mean", "ap_sway_mean_deg", "ap_sway_mean_score"],
    ["Anteroposterior Sway Variability", "ap_sway_sd_deg", "ap_sway_sd_score"],
    ["Step Gap (cm)", "mean_step_gap_cm", "step_gap_score"],
  ],
  jumping_jacks: [
    ["Shoulder Abduction Angle", "shoulder_abduction_angle_mean_deg", "shoulder_abduction_angle_score"],
    ["Hip Abduction Distance", "hip_abduction_distance_mean_norm", "hip_abduction_distance_score"],
    ["Jump", "hip_upward_displacement_mean_norm", "jump_score"],
    ["Arm Leg Sync- open", "arm_leg_open_sync_mean_s", "arm_leg_open_sync_score"],
    ["Arm Leg Sync- close", "arm_leg_close_sync_mean_s", "arm_leg_close_sync_score"],
  ],
};

const EXERCISE_NAMES: Record<string, string> = {
  prone_extension: "Prone Extension",
  supine_flexion: "Supine Flexion",
  one_leg_right_open: "One Leg Standing (Right leg lift, eyes open)",
  one_leg_right_close: "One Leg Standing (Right leg lift, eyes close)",
  one_leg_left_open: "One Leg Standing (Left leg lift, eyes open)",
  one_leg_left_close: "One Leg Standing (Left leg lift, eyes close)",
  tandem_walking_open: "Tandem Walking (Eyes open)",
  tandem_walking_close: "Tandem Walking (Eyes close)",
  jumping_jacks: "Jumping Jacks",
};

// ---------------------------------------------------------------------------
// Render one exercise block
// ---------------------------------------------------------------------------
function renderExerciseBlock(
  doc: jsPDF,
  yPos: number,
  index: number,
  ex: ExerciseVideoData,
) {
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const params = EXERCISE_PARAMS[ex.exerciseId] || [];
  const raw = ex.result?.rawMetrics ?? {};
  const scores = ex.result?.scores ?? {};
  const totalScore = toFiniteNumber(ex.result?.totalScore);
  const maxScore = toFiniteNumber(ex.result?.maxScore);
  const interp = ex.result?.interpretation || "";
  const displayName = EXERCISE_NAMES[ex.exerciseId] || ex.exerciseId;

  // Check space — each exercise block needs ~60-80px minimum
  if (yPos > pageHeight - 90) {
    doc.addPage();
    yPos = 20;
  }

  // Exercise heading
  doc.setFontSize(11);
  doc.setFont("helvetica", "bold");
  doc.setTextColor(0, 0, 0);
  doc.text(`${index})  ${displayName}`, 20, yPos);
  yPos += 5;

  // Build table rows: Parameters | Raw Values | Point Score | Total score
  const body: (string | { content: string; rowSpan?: number; styles?: Record<string, unknown> })[][] = [];

  params.forEach((p, i) => {
    const [label, rawKey, scoreKey] = p;
    const rawVal = raw[rawKey];
    const scoreVal = scores[scoreKey];

    const rawStr = rawVal != null
      ? typeof rawVal === "number" ? fmt(rawVal) : String(rawVal)
      : "";
    const scoreStr = scoreVal != null ? String(scoreVal) : "";

    const row: (string | { content: string; rowSpan?: number; styles?: Record<string, unknown> })[] = [
      label,
      rawStr,
      scoreStr,
    ];

    // Merge "Total score" column across all rows
    if (i === 0) {
      // empty for first two rows, then total+interp in middle rows
    }
    if (i === Math.floor(params.length / 2) - 1) {
      row.push({
        content: `Total point score: ${totalScore ?? ""}`,
        rowSpan: 1,
        styles: { fontStyle: "bold" as unknown as string, fontSize: 9, valign: "middle" },
      });
    } else if (i === Math.floor(params.length / 2)) {
      row.push({
        content: `Interpretation: ${interp}`,
        rowSpan: 1,
        styles: { fontStyle: "italic" as unknown as string, fontSize: 9, valign: "middle" },
      });
    } else {
      row.push("");
    }

    body.push(row);
  });

  autoTable(doc, {
    startY: yPos,
    head: [["Parameters", "Raw Values", "Point Score", "Total score"]],
    body,
    theme: "grid",
    styles: { fontSize: 9, cellPadding: 2.5 },
    headStyles: { fillColor: [0, 100, 150], textColor: 255, fontSize: 9 },
    columnStyles: {
      0: { cellWidth: 48 },
      1: { cellWidth: 30, halign: "center" },
      2: { cellWidth: 26, halign: "center" },
      3: { cellWidth: 60 },
    },
    margin: { left: 20, right: 20 },
  });

  yPos = (doc as any).lastAutoTable.finalY + 3;

  // Additional observations
  const obs = ex.additionalObservation;
  if (ex.exerciseId === "prone_extension" || ex.exerciseId === "supine_flexion") {
    const label = ex.exerciseId === "prone_extension"
      ? "Ability to assume prone extension"
      : "Ability to assume supine flexion";
    doc.setFontSize(9);
    doc.setFont("helvetica", "normal");
    doc.text(`Additional observation:`, 20, yPos + 4);
    yPos += 8;
    doc.text(`${label}- ${obs || ""}`, 20, yPos + 2);
    yPos += 8;
  }

  if (ex.exerciseId.startsWith("tandem_walking")) {
    const nUndersteps = raw.n_understeps;
    doc.setFontSize(9);
    doc.setFont("helvetica", "normal");
    doc.text(`Additional observation:`, 20, yPos + 4);
    yPos += 8;
    doc.text(`Number of under step: `, 20, yPos + 2);
    doc.setFont("helvetica", "bold");
    doc.text(`${nUndersteps ?? ""}`, 20 + doc.getTextWidth("Number of under step: "), yPos + 2);
    doc.setFont("helvetica", "normal");
    yPos += 8;
  }

  if (ex.exerciseId === "jumping_jacks") {
    const totalReps = raw.total_reps;
    const strategy = raw.strategy || raw.balance_strategy || "";
    doc.setFontSize(9);
    doc.setFont("helvetica", "normal");
    doc.text(`Additional observation:`, 20, yPos + 4);
    yPos += 8;
    doc.text(`Number of total correct Jumps: ${obs || totalReps || ""}`, 20, yPos + 2);
    yPos += 5;
    doc.text(`Head trunk hip knee strategy: ${strategy}`, 20, yPos + 2);
    yPos += 8;
  }

  return yPos + 4;
}

// ---------------------------------------------------------------------------
// Main report generation
// ---------------------------------------------------------------------------
export function generateAssessmentReport(assessment: Partial<AssessmentData>): jsPDF {
  const doc = new jsPDF();
  const pageWidth = doc.internal.pageSize.getWidth();
  let yPos = 20;

  // ---- Title ----
  doc.setFontSize(18);
  doc.setFont("helvetica", "bold");
  doc.text("Sensory Processing Assessment Report", pageWidth / 2, yPos, { align: "center" });
  yPos += 8;
  doc.setFontSize(10);
  doc.setFont("helvetica", "normal");
  doc.text("AI-Assisted Vestibular Proprioceptive Processing Assessment", pageWidth / 2, yPos, { align: "center" });
  yPos += 15;
  doc.setDrawColor(0, 120, 180);
  doc.setLineWidth(0.5);
  doc.line(20, yPos, pageWidth - 20, yPos);

  // ---- Demographics ----
  yPos += 15;
  doc.setFontSize(12);
  doc.setFont("helvetica", "bold");
  doc.text("Demographic Details", 20, yPos);
  yPos += 5;

  autoTable(doc, {
    startY: yPos,
    head: [],
    body: [
      ["Child's Name", assessment.demographic?.childName || "N/A"],
      ["Gender", assessment.demographic?.gender || "N/A"],
      ["Date of Birth", assessment.demographic?.dateOfBirth ? format(new Date(assessment.demographic.dateOfBirth), "dd/MM/yyyy") : "N/A"],
      ["Age", assessment.demographic?.calculatedAge || "N/A"],
      ["Date of Assessment", assessment.demographic?.dateOfAssessment ? format(new Date(assessment.demographic.dateOfAssessment), "dd/MM/yyyy") : "N/A"],
      ["Age Group", assessment.ageGroup || "N/A"],
    ],
    theme: "grid",
    styles: { fontSize: 10, cellPadding: 3 },
    columnStyles: { 0: { fontStyle: "bold", cellWidth: 50 }, 1: { cellWidth: 100 } },
    margin: { left: 20, right: 20 },
  });
  yPos = (doc as any).lastAutoTable.finalY + 15;

  // ---- Birth & Medical History ----
  doc.setFontSize(12);
  doc.setFont("helvetica", "bold");
  doc.text("Birth and Medical History", 20, yPos);
  yPos += 5;
  autoTable(doc, {
    startY: yPos,
    head: [],
    body: [
      ["Low Birth Weight", `${assessment.birthMedical?.lowBirthWeight || "N/A"}${assessment.birthMedical?.lowBirthWeightDetails ? ` - ${assessment.birthMedical.lowBirthWeightDetails}` : ""}`],
      ["Premature", `${assessment.birthMedical?.premature || "N/A"}${assessment.birthMedical?.prematureDetails ? ` - ${assessment.birthMedical.prematureDetails}` : ""}`],
      ["Birth Complications", `${assessment.birthMedical?.birthComplications || "N/A"}${assessment.birthMedical?.birthComplicationsDetails ? ` - ${assessment.birthMedical.birthComplicationsDetails}` : ""}`],
      ["Developmental Disability", `${assessment.birthMedical?.developmentalDisability || "N/A"}${assessment.birthMedical?.developmentalDisabilityDetails ? ` - ${assessment.birthMedical.developmentalDisabilityDetails}` : ""}`],
    ],
    theme: "grid",
    styles: { fontSize: 10, cellPadding: 3 },
    columnStyles: { 0: { fontStyle: "bold", cellWidth: 50 }, 1: { cellWidth: 100 } },
    margin: { left: 20, right: 20 },
  });
  yPos = (doc as any).lastAutoTable.finalY + 15;

  // ---- Physical Parameters ----
  doc.setFontSize(12);
  doc.setFont("helvetica", "bold");
  doc.text("Physical Parameters", 20, yPos);
  yPos += 5;
  autoTable(doc, {
    startY: yPos,
    head: [],
    body: [
      ["Height", `${assessment.physicalParameters?.height || "N/A"} m`],
      ["Weight", `${assessment.physicalParameters?.weight || "N/A"} kg`],
      ["BMI", `${assessment.physicalParameters?.bmi || "N/A"} kg/m\u00B2`],
    ],
    theme: "grid",
    styles: { fontSize: 10, cellPadding: 3 },
    columnStyles: { 0: { fontStyle: "bold", cellWidth: 50 }, 1: { cellWidth: 100 } },
    margin: { left: 20, right: 20 },
  });
  yPos = (doc as any).lastAutoTable.finalY + 15;

  // ---- Educational Information ----
  if (assessment.educationalInfo?.enrolledInSchool === "Yes") {
    doc.setFontSize(12);
    doc.setFont("helvetica", "bold");
    doc.text("Educational Information", 20, yPos);
    yPos += 5;
    autoTable(doc, {
      startY: yPos, head: [],
      body: [
        ["Enrolled in School", assessment.educationalInfo.enrolledInSchool || "N/A"],
        ["Type of Education", assessment.educationalInfo.educationType || "N/A"],
        ["Standard / Class", assessment.educationalInfo.standardClass || "N/A"],
        ["School Name", assessment.educationalInfo.schoolName || "N/A"],
      ],
      theme: "grid",
      styles: { fontSize: 10, cellPadding: 3 },
      columnStyles: { 0: { fontStyle: "bold", cellWidth: 50 }, 1: { cellWidth: 100 } },
      margin: { left: 20, right: 20 },
    });
    yPos = (doc as any).lastAutoTable.finalY + 15;
  }

  // ---- Caregiver Information ----
  if (assessment.caregiverInfo?.caregiverName) {
    doc.setFontSize(12);
    doc.setFont("helvetica", "bold");
    doc.text("Caregiver Information", 20, yPos);
    yPos += 5;
    autoTable(doc, {
      startY: yPos, head: [],
      body: [
        ["Caregiver's Name", assessment.caregiverInfo.caregiverName || "N/A"],
        ["Relation to Child", assessment.caregiverInfo.relationToChild || "N/A"],
        ["Contact Number", assessment.caregiverInfo.caregiverContact || "N/A"],
      ],
      theme: "grid",
      styles: { fontSize: 10, cellPadding: 3 },
      columnStyles: { 0: { fontStyle: "bold", cellWidth: 50 }, 1: { cellWidth: 100 } },
      margin: { left: 20, right: 20 },
    });
    yPos = (doc as any).lastAutoTable.finalY + 15;
  }

  // ---- Therapist / Examiner Details ----
  if (yPos > 220) { doc.addPage(); yPos = 20; }
  doc.setFontSize(12);
  doc.setFont("helvetica", "bold");
  doc.text("Therapist / Examiner Details", 20, yPos);
  yPos += 5;
  autoTable(doc, {
    startY: yPos, head: [],
    body: [
      ["Name", assessment.therapistInfo?.therapistName || "N/A"],
      ["Profession", assessment.therapistInfo?.therapistProfession || "N/A"],
      ["License Number", assessment.therapistInfo?.licenseNumber || "N/A"],
      ["Designation", assessment.therapistInfo?.therapistDesignation || "N/A"],
      ["Service Provider", assessment.therapistInfo?.serviceProviderDetails || "N/A"],
    ],
    theme: "grid",
    styles: { fontSize: 10, cellPadding: 3 },
    columnStyles: { 0: { fontStyle: "bold", cellWidth: 50 }, 1: { cellWidth: 100 } },
    margin: { left: 20, right: 20 },
  });
  yPos = (doc as any).lastAutoTable.finalY + 15;

  // ---- Assessment Results ----
  const completedExercises = (assessment.exercises || []).filter(
    (ex) => ex.status === "completed" && toFiniteNumber(ex.result?.totalScore) != null,
  );

  if (completedExercises.length > 0) {
    if (yPos > 200) { doc.addPage(); yPos = 20; }

    doc.setFontSize(12);
    doc.setFont("helvetica", "bold");
    doc.text("Assessment Results", 20, yPos);
    yPos += 6;

    // Assessment-level summary
    const totalAssessmentScore = completedExercises.reduce(
      (acc, ex) => acc + (toFiniteNumber(ex.result?.totalScore) ?? 0), 0,
    );
    const ageYears = inferAgeYears(assessment.ageGroup);
    const norm = assessmentNorm(ageYears);
    const zScore = norm ? (totalAssessmentScore - norm.mean) / norm.sd : null;
    const interp = zScore == null ? "N/A"
      : zScore <= -2 ? "Extremely Below Average"
      : zScore <= -1 ? "Below Average"
      : zScore < 1 ? "Average"
      : zScore < 2 ? "Above Average"
      : "Extremely Above Average";

    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.text(`Completed test: ${completedExercises.length}`, 20, yPos); yPos += 5;
    doc.text(`Total assessment score: ${totalAssessmentScore.toFixed(0)}`, 20, yPos); yPos += 5;
    if (norm) {
      doc.text(`Interpretation: ${interp}`, 20, yPos); yPos += 8;
    }

    // Per-exercise blocks
    completedExercises.forEach((ex, i) => {
      yPos = renderExerciseBlock(doc, yPos, i + 1, ex);
    });
  }

  // ---- Footer on every page ----
  const totalPages = doc.getNumberOfPages();
  for (let p = 1; p <= totalPages; p++) {
    doc.setPage(p);
    const footerY = doc.internal.pageSize.getHeight() - 20;
    doc.setDrawColor(200, 200, 200);
    doc.setLineWidth(0.3);
    doc.line(20, footerY, pageWidth - 20, footerY);
    doc.setFontSize(8);
    doc.setFont("helvetica", "italic");
    doc.setTextColor(100, 100, 100);
    doc.text("This document is auto-generated and does not require a signature.", pageWidth / 2, footerY + 6, { align: "center" });
    doc.setFontSize(7);
    doc.text(`Generated on: ${format(new Date(), "dd/MM/yyyy HH:mm")} | SensoryAssess Pro`, pageWidth / 2, footerY + 11, { align: "center" });
    doc.setTextColor(0, 0, 0);
  }

  return doc;
}

export function downloadReport(assessment: Partial<AssessmentData>) {
  const doc = generateAssessmentReport(assessment);
  const fileName = `Assessment_Report_${assessment.demographic?.childName?.replace(/\s+/g, "_") || "Unknown"}_${format(new Date(), "yyyyMMdd")}.pdf`;
  doc.save(fileName);
}

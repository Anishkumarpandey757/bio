import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import { format } from "date-fns";

import type { AssessmentData } from "@shared/schema";
import { exerciseTypes } from "@shared/schema";

function toFiniteNumber(v: unknown): number | null {
  if (v == null) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
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

export function generateAssessmentReport(assessment: Partial<AssessmentData>): jsPDF {
  const doc = new jsPDF();
  const pageWidth = doc.internal.pageSize.getWidth();
  let yPos = 20;

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

  yPos += 15;
  doc.setFontSize(12);
  doc.setFont("helvetica", "bold");
  doc.text("Demographic Details", 20, yPos);
  yPos += 5;

  const demographicData = [
    ["Child's Name", assessment.demographic?.childName || "N/A"],
    ["Gender", assessment.demographic?.gender || "N/A"],
    ["Date of Birth", assessment.demographic?.dateOfBirth ? format(new Date(assessment.demographic.dateOfBirth), "dd/MM/yyyy") : "N/A"],
    ["Age", assessment.demographic?.calculatedAge || "N/A"],
    ["Date of Assessment", assessment.demographic?.dateOfAssessment ? format(new Date(assessment.demographic.dateOfAssessment), "dd/MM/yyyy") : "N/A"],
    ["Age Group", assessment.ageGroup || "N/A"]
  ];

  autoTable(doc, {
    startY: yPos,
    head: [],
    body: demographicData,
    theme: "grid",
    styles: { fontSize: 10, cellPadding: 3 },
    columnStyles: {
      0: { fontStyle: "bold", cellWidth: 50 },
      1: { cellWidth: 100 }
    },
    margin: { left: 20, right: 20 }
  });

  yPos = (doc as any).lastAutoTable.finalY + 15;

  doc.setFontSize(12);
  doc.setFont("helvetica", "bold");
  doc.text("Birth and Medical History", 20, yPos);
  yPos += 5;

  const medicalData = [
    ["Low Birth Weight", `${assessment.birthMedical?.lowBirthWeight || "N/A"}${assessment.birthMedical?.lowBirthWeightDetails ? ` - ${assessment.birthMedical.lowBirthWeightDetails}` : ""}`],
    ["Premature", `${assessment.birthMedical?.premature || "N/A"}${assessment.birthMedical?.prematureDetails ? ` - ${assessment.birthMedical.prematureDetails}` : ""}`],
    ["Birth Complications", `${assessment.birthMedical?.birthComplications || "N/A"}${assessment.birthMedical?.birthComplicationsDetails ? ` - ${assessment.birthMedical.birthComplicationsDetails}` : ""}`],
    ["Developmental Disability", `${assessment.birthMedical?.developmentalDisability || "N/A"}${assessment.birthMedical?.developmentalDisabilityDetails ? ` - ${assessment.birthMedical.developmentalDisabilityDetails}` : ""}`]
  ];

  autoTable(doc, {
    startY: yPos,
    head: [],
    body: medicalData,
    theme: "grid",
    styles: { fontSize: 10, cellPadding: 3 },
    columnStyles: {
      0: { fontStyle: "bold", cellWidth: 50 },
      1: { cellWidth: 100 }
    },
    margin: { left: 20, right: 20 }
  });

  yPos = (doc as any).lastAutoTable.finalY + 15;

  doc.setFontSize(12);
  doc.setFont("helvetica", "bold");
  doc.text("Physical Parameters", 20, yPos);
  yPos += 5;

  const physicalData = [
    ["Height", `${assessment.physicalParameters?.height || "N/A"} m`],
    ["Weight", `${assessment.physicalParameters?.weight || "N/A"} kg`],
    ["BMI", `${assessment.physicalParameters?.bmi || "N/A"} kg/m²`]
  ];

  autoTable(doc, {
    startY: yPos,
    head: [],
    body: physicalData,
    theme: "grid",
    styles: { fontSize: 10, cellPadding: 3 },
    columnStyles: {
      0: { fontStyle: "bold", cellWidth: 50 },
      1: { cellWidth: 100 }
    },
    margin: { left: 20, right: 20 }
  });

  yPos = (doc as any).lastAutoTable.finalY + 15;

  if (assessment.educationalInfo?.enrolledInSchool === "Yes") {
    doc.setFontSize(12);
    doc.setFont("helvetica", "bold");
    doc.text("Educational Information", 20, yPos);
    yPos += 5;

    const educationData = [
      ["Enrolled in School", assessment.educationalInfo.enrolledInSchool || "N/A"],
      ["Type of Education", assessment.educationalInfo.educationType || "N/A"],
      ["Standard / Class", assessment.educationalInfo.standardClass || "N/A"],
      ["School Name", assessment.educationalInfo.schoolName || "N/A"]
    ];

    autoTable(doc, {
      startY: yPos,
      head: [],
      body: educationData,
      theme: "grid",
      styles: { fontSize: 10, cellPadding: 3 },
      columnStyles: {
        0: { fontStyle: "bold", cellWidth: 50 },
        1: { cellWidth: 100 }
      },
      margin: { left: 20, right: 20 }
    });

    yPos = (doc as any).lastAutoTable.finalY + 15;
  }

  if (assessment.caregiverInfo?.caregiverName) {
    doc.setFontSize(12);
    doc.setFont("helvetica", "bold");
    doc.text("Caregiver Information", 20, yPos);
    yPos += 5;

    const caregiverData = [
      ["Caregiver's Name", assessment.caregiverInfo.caregiverName || "N/A"],
      ["Relation to Child", assessment.caregiverInfo.relationToChild || "N/A"],
      ["Contact Number", assessment.caregiverInfo.caregiverContact || "N/A"]
    ];

    autoTable(doc, {
      startY: yPos,
      head: [],
      body: caregiverData,
      theme: "grid",
      styles: { fontSize: 10, cellPadding: 3 },
      columnStyles: {
        0: { fontStyle: "bold", cellWidth: 50 },
        1: { cellWidth: 100 }
      },
      margin: { left: 20, right: 20 }
    });

    yPos = (doc as any).lastAutoTable.finalY + 15;
  }

  if (yPos > 220) {
    doc.addPage();
    yPos = 20;
  }

  doc.setFontSize(12);
  doc.setFont("helvetica", "bold");
  doc.text("Therapist / Examiner Details", 20, yPos);
  yPos += 5;

  const therapistData = [
    ["Name", assessment.therapistInfo?.therapistName || "N/A"],
    ["Profession", assessment.therapistInfo?.therapistProfession || "N/A"],
    ["License Number", assessment.therapistInfo?.licenseNumber || "N/A"],
    ["Designation", assessment.therapistInfo?.therapistDesignation || "N/A"],
    ["Service Provider", assessment.therapistInfo?.serviceProviderDetails || "N/A"]
  ];

  autoTable(doc, {
    startY: yPos,
    head: [],
    body: therapistData,
    theme: "grid",
    styles: { fontSize: 10, cellPadding: 3 },
    columnStyles: {
      0: { fontStyle: "bold", cellWidth: 50 },
      1: { cellWidth: 100 }
    },
    margin: { left: 20, right: 20 }
  });

  yPos = (doc as any).lastAutoTable.finalY + 15;

  const uploadedExercises = assessment.exercises?.filter(ex => 
    ex.status === "ready" || ex.status === "completed"
  ) || [];

  if (uploadedExercises.length > 0) {
    if (yPos > 200) {
      doc.addPage();
      yPos = 20;
    }

    doc.setFontSize(12);
    doc.setFont("helvetica", "bold");
    doc.text("Assessment Results", 20, yPos);
    yPos += 5;

    const exerciseHeaders = [["Exercise", "Score", "Interpretation", "Key Values"]];

    const completedWithScores = uploadedExercises.filter(ex => {
      const score = toFiniteNumber(ex.result?.totalScore);
      return score != null;
    });

    const totalAssessmentScore = completedWithScores.reduce((acc, ex) => {
      const score = toFiniteNumber(ex.result?.totalScore);
      return acc + (score ?? 0);
    }, 0);

    const ageYears = inferAgeYears(assessment.ageGroup);
    const norm = assessmentNorm(ageYears);
    const zScore = norm ? (totalAssessmentScore - norm.mean) / norm.sd : null;

    const interp = zScore == null
      ? "N/A"
      : zScore <= -2
      ? "Extremely Below Average"
      : zScore <= -1
      ? "Below Average"
      : zScore < 1
      ? "Average"
      : zScore < 2
      ? "Above Average"
      : "Extremely Above Average";

    const exerciseData = uploadedExercises.map(ex => {
      const exerciseInfo = exerciseTypes.find(e => e.id === ex.exerciseId);
      const score = toFiniteNumber(ex.result?.totalScore);
      const maxScore = toFiniteNumber(ex.result?.maxScore);
      const scoreText = score == null
        ? "N/A"
        : maxScore == null
        ? `${score}`
        : `${score}/${maxScore}`;

      const rawMetrics = ex.result?.rawMetrics ?? {};
      const topMetrics = Object.entries(rawMetrics)
        .filter(([, v]) => ["number", "string", "boolean"].includes(typeof v))
        .slice(0, 4)
        .map(([k, v]) => `${k}: ${String(v)}`)
        .join(" | ");

      return [
        exerciseInfo?.name || ex.exerciseId,
        scoreText,
        ex.result?.interpretation || "N/A",
        topMetrics || "No metrics",
      ];
    });

    if (yPos > 180) {
      doc.addPage();
      yPos = 20;
    }

    doc.setFontSize(11);
    doc.setFont("helvetica", "bold");
    doc.text("Assessment-Level Summary", 20, yPos);
    yPos += 6;
    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.text(`Completed exercises: ${completedWithScores.length}`, 20, yPos);
    yPos += 5;
    doc.text(`Total assessment score (sum): ${totalAssessmentScore.toFixed(2)}`, 20, yPos);
    yPos += 5;
    if (norm) {
      doc.text(`Norm mean/sd (${ageYears}y): ${norm.mean}/${norm.sd}`, 20, yPos);
      yPos += 5;
      doc.text(`z-score: ${zScore?.toFixed(3)} | Interpretation: ${interp}`, 20, yPos);
      yPos += 6;
    } else {
      doc.text("z-score: N/A (age group not 6y/7y)", 20, yPos);
      yPos += 6;
    }

    autoTable(doc, {
      startY: yPos,
      head: exerciseHeaders,
      body: exerciseData,
      theme: "striped",
      styles: { fontSize: 9, cellPadding: 3 },
      headStyles: { fillColor: [0, 120, 180], textColor: 255 },
      columnStyles: {
        0: { cellWidth: 42 },
        1: { cellWidth: 22 },
        2: { cellWidth: 40 },
        3: { cellWidth: 86 },
      },
      margin: { left: 20, right: 20 }
    });

    yPos = (doc as any).lastAutoTable.finalY + 15;
  }

  const footerY = doc.internal.pageSize.getHeight() - 25;
  doc.setDrawColor(200, 200, 200);
  doc.setLineWidth(0.3);
  doc.line(20, footerY, pageWidth - 20, footerY);

  doc.setFontSize(8);
  doc.setFont("helvetica", "italic");
  doc.setTextColor(100, 100, 100);
  doc.text(
    "This document is auto-generated and does not require a signature.",
    pageWidth / 2,
    footerY + 8,
    { align: "center" }
  );

  doc.setFontSize(7);
  doc.text(
    `Generated on: ${format(new Date(), "dd/MM/yyyy HH:mm")} | SensoryAssess Pro`,
    pageWidth / 2,
    footerY + 14,
    { align: "center" }
  );

  return doc;
}

export function downloadReport(assessment: Partial<AssessmentData>) {
  const doc = generateAssessmentReport(assessment);
  const fileName = `Assessment_Report_${assessment.demographic?.childName?.replace(/\s+/g, "_") || "Unknown"}_${format(new Date(), "yyyyMMdd")}.pdf`;
  doc.save(fileName);
}

import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import { format } from "date-fns";

import type { AssessmentData } from "@shared/schema";
import { exerciseTypes } from "@shared/schema";

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

    const isStandardAgeGroup = assessment.ageGroup?.includes("6 years") || assessment.ageGroup?.includes("7 years");

    const exerciseHeaders = isStandardAgeGroup 
      ? [["Exercise", "Values", "Score"]]
      : [["Exercise", "Values"]];

    const exerciseData = uploadedExercises.map(ex => {
      const exerciseInfo = exerciseTypes.find(e => e.id === ex.exerciseId);
      const values = ex.result?.values 
        ? Object.entries(ex.result.values).map(([k, v]) => `${k}: ${v}`).join(", ")
        : "Pending Analysis";
      
      if (isStandardAgeGroup) {
        return [exerciseInfo?.name || ex.exerciseId, values, ex.result?.score?.toString() || "N/A"];
      }
      return [exerciseInfo?.name || ex.exerciseId, values];
    });

    autoTable(doc, {
      startY: yPos,
      head: exerciseHeaders,
      body: exerciseData,
      theme: "striped",
      styles: { fontSize: 9, cellPadding: 3 },
      headStyles: { fillColor: [0, 120, 180], textColor: 255 },
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

#!/usr/bin/env node

/**
 * End-to-End Integration Test Script
 * Tests the complete flow from video upload to assessment result
 */

import fs from "fs";
import path from "path";
import FormData from "form-data";
import fetch from "node-fetch";

const FASTAPI_URL = process.env.FASTAPI_URL || "http://localhost:8000";
const EXPRESS_URL = process.env.EXPRESS_URL || "http://localhost:5000";

interface TestResult {
  name: string;
  success: boolean;
  duration: number;
  error?: string;
}

const results: TestResult[] = [];

async function test(name: string, fn: () => Promise<void>) {
  const start = Date.now();
  try {
    await fn();
    results.push({ name, success: true, duration: Date.now() - start });
    console.log(`✅ ${name} (${Date.now() - start}ms)`);
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    results.push({ 
      name, 
      success: false, 
      duration: Date.now() - start,
      error: errorMsg 
    });
    console.log(`❌ ${name}\n   ${errorMsg}`);
  }
}

async function main() {
  console.log("🧪 Running End-to-End Integration Tests\n");

  // Test 1: FastAPI Health Check
  await test("FastAPI Health Check", async () => {
    const response = await fetch(`${FASTAPI_URL}/health`);
    if (!response.ok) throw new Error(`FastAPI returned ${response.status}`);
  });

  // Test 2: Express Health Check (via backend health)
  await test("Express Backend Health", async () => {
    const response = await fetch(`${EXPRESS_URL}/api/backend-health`);
    if (!response.ok) throw new Error(`Express returned ${response.status}`);
    const data = await response.json() as Record<string, unknown>;
    if (data.status !== "ok") throw new Error("Backend health status not ok");
  });

  // Test 3: Create a test video file (if it doesn't exist)
  const testVideoPath = path.join(process.cwd(), "test-video.mp4");
  await test("Create Test Video", async () => {
    if (fs.existsSync(testVideoPath)) {
      console.log("   (Using existing test video)");
      return;
    }
    // Create a minimal valid MP4 file for testing
    const ftyp = Buffer.from([
      0x00, 0x00, 0x00, 0x20, 0x66, 0x74, 0x79, 0x70,
      0x69, 0x73, 0x6f, 0x6d, 0x00, 0x00, 0x02, 0x00,
      0x69, 0x73, 0x6f, 0x6d, 0x69, 0x73, 0x6f, 0x32,
      0x6d, 0x70, 0x34, 0x31
    ]);
    fs.writeFileSync(testVideoPath, ftyp);
  });

  // Test 4: Process Exercise via Express
  await test("Process Exercise (Prone Extension)", async () => {
    if (!fs.existsSync(testVideoPath)) {
      throw new Error("Test video not created");
    }

    const formData = new FormData();
    formData.append("exerciseId", "prone_extension");
    formData.append("ageGroup", "7 years");
    formData.append("sideVideo", fs.createReadStream(testVideoPath), "test-side.mp4");

    const response = await fetch(`${EXPRESS_URL}/api/process-exercise`, {
      method: "POST",
      body: formData,
      headers: formData.getHeaders?.() || {}
    });

    if (!response.ok) {
      const errorBody = await response.text();
      throw new Error(`Failed with status ${response.status}: ${errorBody}`);
    }

    const result = await response.json() as Record<string, unknown>;
    if (!result.success && result.error) {
      throw new Error(`Processing error: ${result.error}`);
    }
  });

  // Test 5: Verify Database Connection
  await test("Database Connection", async () => {
    const response = await fetch(`${EXPRESS_URL}/api/assessments`);
    if (!response.ok) throw new Error(`Database endpoint returned ${response.status}`);
    await response.json();
  });

  // Test 6: Create Assessment
  await test("Create Assessment", async () => {
    const assessment = {
      demographic: {
        childName: "Test Child",
        gender: "Male",
        dateOfBirth: "2015-01-15",
        dateOfAssessment: "2024-02-16"
      },
      birthMedical: {
        lowBirthWeight: "No",
        premature: "No",
        birthComplications: "No",
        developmentalDisability: "No"
      },
      physicalParameters: {
        height: 1.3,
        weight: 35
      },
      educationalInfo: {
        enrolledInSchool: "Yes",
        educationType: "Mainstream"
      },
      caregiverInfo: {},
      therapistInfo: {
        therapistName: "Test Therapist",
        therapistProfession: "OT",
        therapistDesignation: "Lead",
        serviceProviderDetails: "Test Clinic"
      },
      ageGroup: "7 years 0 months – 7 years 11 months",
      exercises: [],
      status: "draft"
    };

    const response = await fetch(`${EXPRESS_URL}/api/assessments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(assessment)
    });

    if (!response.ok) throw new Error(`Failed with status ${response.status}`);
    const result = await response.json() as Record<string, unknown>;
    if (!result.id) throw new Error("Assessment creation did not return ID");
  });

  // Cleanup
  if (fs.existsSync(testVideoPath)) {
    fs.unlinkSync(testVideoPath);
  }

  // Print Results Summary
  console.log("\n📊 Test Results Summary");
  console.log("=======================");
  const passed = results.filter(r => r.success).length;
  const total = results.length;
  const totalDuration = results.reduce((sum, r) => sum + r.duration, 0);
  
  console.log(`\nPassed: ${passed}/${total}`);
  console.log(`Total Duration: ${totalDuration}ms`);

  if (results.some(r => !r.success)) {
    console.log("\n⚠️  Failed Tests:");
    results
      .filter(r => !r.success)
      .forEach(r => console.log(`  - ${r.name}: ${r.error}`));
    process.exit(1);
  } else {
    console.log("\n✅ All tests passed!");
    process.exit(0);
  }
}

main().catch(error => {
  console.error("Fatal error:", error);
  process.exit(1);
});

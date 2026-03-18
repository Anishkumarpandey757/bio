import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { insertAssessmentDBSchema } from "@shared/schema";
import { z } from "zod";
import multer from "multer";
import path from "path";
import fs from "fs";
import axios from "axios";
import FormData from "form-data";

// Configure multer for video uploads
const uploadDir = path.join(process.cwd(), "uploads");
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir, { recursive: true });
}

const storage_multer = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    cb(null, `${Date.now()}-${file.originalname}`);
  }
});

const upload = multer({
  storage: storage_multer,
  fileFilter: (req, file, cb) => {
    const validMimes = ["video/mp4", "video/quicktime", "video/mov"];
    if (validMimes.includes(file.mimetype)) {
      cb(null, true);
    } else {
      cb(new Error("Invalid file type"));
    }
  },
  limits: { fileSize: 500 * 1024 * 1024 } // 500MB
});

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  
  app.post("/api/assessments", async (req, res) => {
    try {
      const validatedData = insertAssessmentDBSchema.parse(req.body);
      const assessment = await storage.createAssessment(validatedData);
      res.status(201).json(assessment);
    } catch (error) {
      if (error instanceof z.ZodError) {
        res.status(400).json({ error: "Validation failed", details: error.errors });
      } else {
        console.error("Error creating assessment:", error);
        res.status(500).json({ error: "Failed to create assessment" });
      }
    }
  });

  app.get("/api/assessments", async (_req, res) => {
    try {
      const assessments = await storage.getAllAssessments();
      res.json(assessments);
    } catch (error) {
      console.error("Error fetching assessments:", error);
      res.status(500).json({ error: "Failed to fetch assessments" });
    }
  });

  app.get("/api/assessments/:id", async (req, res) => {
    try {
      const id = parseInt(req.params.id, 10);
      if (isNaN(id)) {
        return res.status(400).json({ error: "Invalid assessment ID" });
      }
      const assessment = await storage.getAssessment(id);
      if (!assessment) {
        return res.status(404).json({ error: "Assessment not found" });
      }
      res.json(assessment);
    } catch (error) {
      console.error("Error fetching assessment:", error);
      res.status(500).json({ error: "Failed to fetch assessment" });
    }
  });

  app.patch("/api/assessments/:id", async (req, res) => {
    try {
      const id = parseInt(req.params.id, 10);
      if (isNaN(id)) {
        return res.status(400).json({ error: "Invalid assessment ID" });
      }
      
      const partialSchema = insertAssessmentDBSchema.partial();
      const validatedData = partialSchema.parse(req.body);
      
      const assessment = await storage.updateAssessment(id, validatedData);
      if (!assessment) {
        return res.status(404).json({ error: "Assessment not found" });
      }
      res.json(assessment);
    } catch (error) {
      if (error instanceof z.ZodError) {
        res.status(400).json({ error: "Validation failed", details: error.errors });
      } else {
        console.error("Error updating assessment:", error);
        res.status(500).json({ error: "Failed to update assessment" });
      }
    }
  });

  app.delete("/api/assessments/:id", async (req, res) => {
    try {
      const id = parseInt(req.params.id, 10);
      if (isNaN(id)) {
        return res.status(400).json({ error: "Invalid assessment ID" });
      }
      const deleted = await storage.deleteAssessment(id);
      if (!deleted) {
        return res.status(404).json({ error: "Assessment not found" });
      }
      res.status(204).send();
    } catch (error) {
      console.error("Error deleting assessment:", error);
      res.status(500).json({ error: "Failed to delete assessment" });
    }
  });

  // Video processing routes
  app.post("/api/process-exercise", 
    upload.fields([
      { name: "frontVideo", maxCount: 1 },
      { name: "sideVideo", maxCount: 1 }
    ]),
    async (req, res) => {
      try {
        const { exerciseId, ageGroup, assessmentId } = req.body;
        const files = req.files as { [fieldname: string]: Express.Multer.File[] } | undefined;

        if (!exerciseId || !ageGroup) {
          return res.status(400).json({ error: "Missing exerciseId or ageGroup" });
        }

        const frontVideo = files?.frontVideo?.[0];
        const sideVideo = files?.sideVideo?.[0];

        if (!frontVideo && !sideVideo) {
          return res.status(400).json({ error: "At least one video is required" });
        }

        // Call FastAPI backend to process the exercise.
        // We use axios + `form-data` so files can be streamed (no huge memory usage)
        // and multipart boundaries are generated correctly.
        const formData = new FormData();
        formData.append("age_group", String(ageGroup));

        if (assessmentId) {
          formData.append("assessmentId", String(assessmentId));
        }

        if (frontVideo) {
          formData.append("front_video", fs.createReadStream(frontVideo.path), {
            filename: frontVideo.originalname,
            contentType: frontVideo.mimetype,
          });
        }
        if (sideVideo) {
          formData.append("side_video", fs.createReadStream(sideVideo.path), {
            filename: sideVideo.originalname,
            contentType: sideVideo.mimetype,
          });
        }

        const fastApiUrl = process.env.FASTAPI_URL || "http://localhost:8000";
        const fastApiResponse = await axios.post(
          `${fastApiUrl}/api/process-exercise-files/${exerciseId}`,
          formData,
          {
            headers: formData.getHeaders(),
            maxBodyLength: Infinity,
            maxContentLength: Infinity,
            validateStatus: () => true,
          },
        );

        if (fastApiResponse.status >= 400) {
          const errorBody =
            typeof fastApiResponse.data === "string"
              ? fastApiResponse.data
              : JSON.stringify(fastApiResponse.data);
          console.error("FastAPI error:", errorBody);
          return res.status(fastApiResponse.status).json({
            error: "Failed to process exercise",
            details: errorBody,
          });
        }

        const result = fastApiResponse.data as Record<string, unknown>;

        // Clean up temp files
        if (frontVideo) fs.unlinkSync(frontVideo.path);
        if (sideVideo) fs.unlinkSync(sideVideo.path);

        res.json(result);
      } catch (error) {
        console.error("Error processing exercise:", error);
        res.status(500).json({ 
          error: "Failed to process exercise", 
          details: error instanceof Error ? error.message : String(error)
        });
      }
    }
  );

  // Health check for FastAPI backend
  app.get("/api/backend-health", async (req, res) => {
    try {
      const fastApiUrl = process.env.FASTAPI_URL || "http://localhost:8000";
      const response = await fetch(`${fastApiUrl}/health`);
      if (response.ok) {
        res.json({ status: "ok", backend: "fastapi" });
      } else {
        res.status(503).json({ status: "unavailable", backend: "fastapi" });
      }
    } catch (error) {
      res.status(503).json({ 
        status: "unavailable", 
        backend: "fastapi",
        error: error instanceof Error ? error.message : "Unknown error"
      });
    }
  });

  return httpServer;
}

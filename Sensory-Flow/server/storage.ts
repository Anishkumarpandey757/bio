import {
  type SelectUser,
  type InsertUserDB,
  type SelectAssessment,
  type InsertAssessmentDB,
} from "@shared/schema";
import { MongoClient, Db } from "mongodb";

export interface IStorage {
  getUser(id: number): Promise<SelectUser | undefined>;
  getUserByUsername(username: string): Promise<SelectUser | undefined>;
  createUser(user: InsertUserDB): Promise<SelectUser>;
  
  createAssessment(assessment: InsertAssessmentDB): Promise<SelectAssessment>;
  getAssessment(id: number): Promise<SelectAssessment | undefined>;
  getAllAssessments(): Promise<SelectAssessment[]>;
  updateAssessment(id: number, assessment: Partial<InsertAssessmentDB>): Promise<SelectAssessment | undefined>;
  deleteAssessment(id: number): Promise<boolean>;
}

let mongoClient: MongoClient | null = null;
let mongoDb: Db | null = null;

async function getMongoDb(): Promise<Db> {
  if (mongoDb) return mongoDb;
  const uri = process.env.MONGODB_URI;
  if (!uri) {
    throw new Error("MONGODB_URI is not set. Please configure MongoDB Atlas URI in .env");
  }
  mongoClient = new MongoClient(uri);
  await mongoClient.connect();
  mongoDb = mongoClient.db("sensory_flow");
  return mongoDb;
}

export class DatabaseStorage implements IStorage {
  async getUser(id: number): Promise<SelectUser | undefined> {
    return undefined;
  }

  async getUserByUsername(username: string): Promise<SelectUser | undefined> {
    return undefined;
  }

  async createUser(insertUser: InsertUserDB): Promise<SelectUser> {
    throw new Error("User storage not implemented for MongoDB in this project");
  }

  async createAssessment(insertAssessment: InsertAssessmentDB): Promise<SelectAssessment> {
    const db = await getMongoDb();
    const counters = db.collection<{ _id: string; seq: number }>("counters");
    const assessments = db.collection("assessments");

    const counter = await counters.findOneAndUpdate(
      { _id: "assessment_id" },
      { $inc: { seq: 1 } },
      { upsert: true, returnDocument: "after" },
    );
    const id = Number(counter?.seq ?? 1);

    const doc: SelectAssessment = {
      id,
      demographic: insertAssessment.demographic as any,
      birthMedical: insertAssessment.birthMedical as any,
      physicalParameters: insertAssessment.physicalParameters as any,
      educationalInfo: insertAssessment.educationalInfo as any,
      caregiverInfo: (insertAssessment.caregiverInfo as any) ?? null,
      therapistInfo: insertAssessment.therapistInfo as any,
      ageGroup: insertAssessment.ageGroup,
      exercises: insertAssessment.exercises as any,
      status: insertAssessment.status ?? "draft",
      createdAt: new Date(),
      completedAt: null,
    };

    await assessments.insertOne(doc as any);
    return doc;
  }

  async getAssessment(id: number): Promise<SelectAssessment | undefined> {
    const db = await getMongoDb();
    const assessments = db.collection<SelectAssessment>("assessments");
    const assessment = await assessments.findOne({ id });
    return assessment ?? undefined;
  }

  async getAllAssessments(): Promise<SelectAssessment[]> {
    const db = await getMongoDb();
    const assessments = db.collection<SelectAssessment>("assessments");
    return await assessments.find({}).sort({ createdAt: -1 }).toArray();
  }

  async updateAssessment(id: number, updateData: Partial<InsertAssessmentDB>): Promise<SelectAssessment | undefined> {
    const db = await getMongoDb();
    const assessments = db.collection<SelectAssessment>("assessments");
    const result = await assessments.findOneAndUpdate(
      { id },
      { $set: updateData as any },
      { returnDocument: "after" },
    );
    return result ?? undefined;
  }

  async deleteAssessment(id: number): Promise<boolean> {
    const db = await getMongoDb();
    const assessments = db.collection("assessments");
    const result = await assessments.deleteOne({ id });
    return result.deletedCount > 0;
  }
}

export const storage = new DatabaseStorage();

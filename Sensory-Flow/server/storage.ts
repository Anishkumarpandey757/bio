import { 
  users, 
  assessments,
  type SelectUser, 
  type InsertUserDB,
  type SelectAssessment,
  type InsertAssessmentDB
} from "@shared/schema";
import { db } from "./db";
import { eq, desc } from "drizzle-orm";

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

export class DatabaseStorage implements IStorage {
  async getUser(id: number): Promise<SelectUser | undefined> {
    const [user] = await db.select().from(users).where(eq(users.id, id));
    return user || undefined;
  }

  async getUserByUsername(username: string): Promise<SelectUser | undefined> {
    const [user] = await db.select().from(users).where(eq(users.username, username));
    return user || undefined;
  }

  async createUser(insertUser: InsertUserDB): Promise<SelectUser> {
    const [user] = await db
      .insert(users)
      .values(insertUser)
      .returning();
    return user;
  }

  async createAssessment(insertAssessment: InsertAssessmentDB): Promise<SelectAssessment> {
    const [assessment] = await db
      .insert(assessments)
      .values(insertAssessment)
      .returning();
    return assessment;
  }

  async getAssessment(id: number): Promise<SelectAssessment | undefined> {
    const [assessment] = await db.select().from(assessments).where(eq(assessments.id, id));
    return assessment || undefined;
  }

  async getAllAssessments(): Promise<SelectAssessment[]> {
    return await db.select().from(assessments).orderBy(desc(assessments.createdAt));
  }

  async updateAssessment(id: number, updateData: Partial<InsertAssessmentDB>): Promise<SelectAssessment | undefined> {
    const [assessment] = await db
      .update(assessments)
      .set(updateData)
      .where(eq(assessments.id, id))
      .returning();
    return assessment || undefined;
  }

  async deleteAssessment(id: number): Promise<boolean> {
    const result = await db.delete(assessments).where(eq(assessments.id, id)).returning();
    return result.length > 0;
  }
}

export const storage = new DatabaseStorage();

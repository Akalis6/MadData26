import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
    UniversityTable: defineTable({
        name: v.string(),
        abbreviation: v.string(),
        location: v.string()
    }),
    CourseTable: defineTable({
        name: v.string(),
        credits: v.number(),
        breadth: v.array(v.string()),
        //prerequirements: v.array(v.string()),
        prerequirements: v.any(),
        generalEd: v.optional(v.string()),
        courseID: v.string(),
        level: v.optional(v.string()),
        university: v.id("UniversityTable"),
        repeatable: v.boolean(),
        description: v.string(),
        ethnicstudies: v.boolean(),
    }),
    GERequirements: defineTable({
        name: v.string(),
        credits: v.number(),
    }),
    MajorsList: defineTable({
        majorName: v.string(),
        degreeType: v.string(),
        University: v.id("UniversityTable"),
    }),
    MajorReqs: defineTable({
        major: v.string(),
        requirementGroups: v.array(v.object({
            groupId: v.string(),
            ruleType: v.string(),
            requiredCount: v.union(v.null(), v.number()),
            requiredCredits: v.union(v.null(), v.number(),),
            courses: v.array(v.string())
        })),
    }),
    DegreeReqs: defineTable({
        name: v.string(), //req over will be metadata (BA/BS) - user has own table
        mathematics: v.number(),
        language: v.boolean(),
        ethnicstudies: v.boolean(),
        LSBreadth: v.object({
            humanities: v.number(),
            literature: v.number(), // linked into humanities
            socialscience: v.number(),
            NaturalScience: v.number(),
            BiologicalScience: v.number(),
            PhysicalScience: v.number(),
        }),
        LASCoursework: v.number(),
        InterAdvCoursework: v.number(),
        TotalCredits: v.number(),
        GPA: v.number(),
    }),
    StudentPlans: defineTable({
  // If you don’t have auth yet, use a fixed userId like "local-dev".
  // If you do have auth, store ctx.auth.getUserIdentity().subject instead.
  userId: v.string(),

  // Optional: helps if you support multiple schools
  university: v.optional(v.id("UniversityTable")),

  // "dars" means it came from an uploaded report; "manual" if from planner
  source: v.union(v.literal("dars"), v.literal("manual")),

  // When this plan was last updated
  updatedAt: v.number(),

  // Helpful metadata (optional)
  darsFileName: v.optional(v.string()),
  darsFileHash: v.optional(v.string()), // prevents re-upload duplicates

  // Flattened course list (canonical!)
  courses: v.array(
    v.object({
      term: v.string(), // "Fall 2022"
      courseId: v.string(), // "COMP SCI 300"
      title: v.string(),
      credits: v.number(),
      status: v.union(v.literal("completed"), v.literal("in_progress"), v.literal("planned")),
      grade: v.optional(v.string()), // only for DARS typically
      flags: v.optional(v.array(v.string())), // future-proof
    })
  ),
})
  .index("by_user_source", ["userId", "source"])
  .index("by_user", ["userId"]),
});
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
        breadth: v.string(),
        prerequirements: v.array(v.string()),
        generalEd: v.string(),
        courseID: v.string(),
        level: v.string(),
        university: v.id("UniversityTable"),
        repeatable: v.boolean(),
        description: v.string(),
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
        course: v.id("CourseTable"),
        groupID: v.number(),
        majorName: v.string(),
        majorID: v.id("MajorsList"),
        creditsNeeded: v.string(),
        done: v.boolean(),
    }),
    DegreeReqs: defineTable({
        name: v.string(), //req over will be metadata (BA/BS) - user has own table
        mathematics: v.number(),
        language: v.boolean(),
        LSBreadth: v.object({
            humanities: v.number(),
            literature: v.number(), // linked into humanities
            socialscience: v.number(),
            BiologicalScience: v.number(),
            PhysicalScience: v.number(),
        }),
        LASCoursework: v.number(),
        InterAdvCoursework: v.number(),
        TotalCredits: v.number(),
        GPA: v.number(),
    }),
});
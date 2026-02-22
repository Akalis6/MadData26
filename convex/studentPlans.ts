import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

function canon(x: string) {
  return String(x).trim().toUpperCase().replace(/\s+/g, " ");
}

export const upsert = mutation({
  args: {
    userId: v.string(),
    source: v.union(v.literal("dars"), v.literal("manual")),
    university: v.optional(v.id("UniversityTable")),
    darsFileName: v.optional(v.string()),
    darsFileHash: v.optional(v.string()),
    courses: v.array(
      v.object({
        term: v.string(),
        courseId: v.string(),
        title: v.string(),
        credits: v.number(),
        status: v.union(v.literal("completed"), v.literal("in_progress"), v.literal("planned")),
        grade: v.optional(v.string()),
        flags: v.optional(v.array(v.string())),
      })
    ),
  },
  handler: async (ctx, args) => {
    // Canonicalize course IDs so matching is consistent everywhere
    const normalizedCourses = args.courses.map((c) => ({
      ...c,
      courseId: canon(c.courseId),
      term: c.term.trim(),
      title: String(c.title ?? "").trim(),
      credits: Number(c.credits ?? 0),
    }));

    const existing = await ctx.db
      .query("StudentPlans")
      .withIndex("by_user_source", (q) => q.eq("userId", args.userId).eq("source", args.source))
      .first();

    const payload = {
      userId: args.userId,
      source: args.source,
      university: args.university,
      updatedAt: Date.now(),
      darsFileName: args.darsFileName,
      darsFileHash: args.darsFileHash,
      courses: normalizedCourses,
    };

    if (existing) {
      await ctx.db.patch(existing._id, payload);
      return existing._id;
    }
    return await ctx.db.insert("StudentPlans", payload);
  },
});

export const get = query({
  args: {
    userId: v.string(),
    source: v.union(v.literal("dars"), v.literal("manual")),
  },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("StudentPlans")
      .withIndex("by_user_source", (q) => q.eq("userId", args.userId).eq("source", args.source))
      .first();
  },
});
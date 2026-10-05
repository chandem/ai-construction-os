# Lesson 16 — Project Data Agent

The Construction AI Agent can now call a project-data tool that is bound to the
already-authorized project ID.

The endpoint first verifies the authenticated user is a member of the project's
organization. Only then is a Gemini-callable function created with that project ID
closed over it. Gemini therefore cannot choose another project ID.

The tool reads existing project records from:
- activities
- materials
- equipment
- cost_entries
- project_risks

It returns a compact deterministic summary for Gemini to explain. It does not
write to the database.

The implementation intentionally uses the existing schema; no new Supabase tables
or RLS policies are required for this lesson.

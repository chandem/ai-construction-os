import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const supabaseUrl = (import.meta.env.VITE_SUPABASE_URL || "").trim();
const supabaseKey = (import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || "").trim();

function makeClient(): SupabaseClient {
  // Avoid crashing the whole SPA when env vars are missing in a bad deploy.
  if (!supabaseUrl || !supabaseKey) {
    console.error(
      "Supabase env missing. Set VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY on Vercel.",
    );
    return createClient("https://placeholder.supabase.co", "public-anon-key");
  }
  return createClient(supabaseUrl, supabaseKey);
}

export const supabase = makeClient();
export { supabaseUrl, supabaseKey };

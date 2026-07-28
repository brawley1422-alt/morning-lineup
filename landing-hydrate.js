import { getSession, supabase } from "./auth/session.js";

(async function hydrate(){
  try {
    const session = await getSession();
    // Signed out is a first-class state: the page is already fully readable,
    // so we leave the "Sign In" link alone and stop here. No bounce, no gate.
    if (!session) return;

    const authLink = document.getElementById("mast-auth");
    if (authLink) {
      authLink.textContent = "Account";
      authLink.href = "settings/";
    }

    const { data: profile } = await supabase
      .from("profiles")
      .select("display_name")
      .eq("id", session.user.id)
      .maybeSingle();
    const name = (profile && profile.display_name) || session.user.email?.split("@")[0] || "Reader";
    document.getElementById("greet-reader").textContent = name + ".";
    document.getElementById("kick-reader").textContent = name;

    const { data: followed } = await supabase
      .from("followed_teams")
      .select("team_slug, position")
      .order("position", { ascending: true })
      .limit(1);
    if (followed && followed.length) {
      window.__heroTeamSlug = followed[0].team_slug;
      if (typeof window.fillHero === "function") window.fillHero(followed[0].team_slug);
    }
  } catch (err) {
    console.warn("landing hydrate failed", err);
  }
})();

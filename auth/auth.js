// Auth page controller — signup, login, password reset request, Google OAuth.
// Redirects to ../home/ on successful session. Relies on Supabase JS client via esm.sh.

import { supabase } from "./session.js";

const HOME_PATH = "../home/";
const RESET_REDIRECT = new URL("reset.html", window.location.href).toString();

const form = document.getElementById("auth-form");
const errorBox = document.getElementById("auth-error");
const noticeBox = document.getElementById("auth-notice");
const submitBtn = document.getElementById("auth-submit");
const toggleBtn = document.getElementById("toggle-mode");
const forgotBtn = document.getElementById("forgot-link");
const googleBtn = document.getElementById("auth-google");
const nameField = document.getElementById("name-field");
const passwordField = document.getElementById("password-field");
const modeTitle = document.getElementById("mode-title");
const modeNum = document.getElementById("mode-num");
const modeTag = document.getElementById("mode-tag");
const modeLede = document.getElementById("mode-lede");

const MODES = {
  login: {
    num: "01",
    title: "Sign In",
    tag: "Members Desk",
    lede: "Welcome back. Your personalized briefing awaits.",
    submit: "Sign In",
    toggle: "Need an account? Sign up",
    showName: false,
    showPassword: true,
    passwordAutocomplete: "current-password",
  },
  signup: {
    num: "01",
    title: "Sign Up",
    tag: "New Subscriber",
    lede: "Claim a press pass. Pick your teams. Make this paper yours.",
    submit: "Create Account",
    toggle: "Already a member? Sign in",
    showName: true,
    showPassword: true,
    passwordAutocomplete: "new-password",
  },
  forgot: {
    num: "02",
    title: "Forgot Password",
    tag: "Locker Room",
    lede: "We'll email you a link to choose a new password.",
    submit: "Send Reset Link",
    toggle: "Back to sign in",
    showName: false,
    showPassword: false,
    passwordAutocomplete: "",
  },
};

let mode = "login";

function applyMode() {
  const m = MODES[mode];
  modeNum.textContent = m.num;
  modeTitle.textContent = m.title;
  modeTag.textContent = m.tag;
  modeLede.textContent = m.lede;
  submitBtn.textContent = m.submit;
  toggleBtn.textContent = m.toggle;
  nameField.hidden = !m.showName;
  passwordField.hidden = !m.showPassword;
  const pw = passwordField.querySelector("input");
  pw.required = m.showPassword;
  pw.autocomplete = m.passwordAutocomplete;
  clearMessages();
}

function clearMessages() {
  errorBox.hidden = true;
  errorBox.textContent = "";
  noticeBox.hidden = true;
  noticeBox.textContent = "";
}

function showError(msg) {
  errorBox.textContent = msg;
  errorBox.hidden = false;
  noticeBox.hidden = true;
}

function showNotice(msg) {
  noticeBox.textContent = msg;
  noticeBox.hidden = false;
  errorBox.hidden = true;
}

async function handleSubmit(e) {
  e.preventDefault();
  clearMessages();
  const fd = new FormData(form);
  const email = (fd.get("email") || "").toString().trim();
  const password = (fd.get("password") || "").toString();
  const displayName = (fd.get("display_name") || "").toString().trim();

  if (!email) {
    showError("Email is required.");
    return;
  }

  submitBtn.disabled = true;
  try {
    if (mode === "login") {
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) throw error;
      window.location.href = HOME_PATH;
    } else if (mode === "signup") {
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: { data: { display_name: displayName || null } },
      });
      if (error) throw error;
      // If email confirmation is off, session is active immediately.
      const { data } = await supabase.auth.getSession();
      if (data?.session) {
        window.location.href = HOME_PATH;
      } else {
        showNotice("Check your inbox for a confirmation link.");
      }
    } else if (mode === "forgot") {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: RESET_REDIRECT,
      });
      // Always show the same message — no user enumeration.
      if (error && error.status && error.status >= 500) throw error;
      showNotice("If an account exists for that email, we sent a reset link.");
    }
  } catch (err) {
    showError(err?.message || "Something went wrong. Try again.");
  } finally {
    submitBtn.disabled = false;
  }
}

toggleBtn.addEventListener("click", () => {
  if (mode === "login") mode = "signup";
  else mode = "login";
  applyMode();
});

forgotBtn.addEventListener("click", () => {
  mode = "forgot";
  applyMode();
});

googleBtn.addEventListener("click", async () => {
  clearMessages();
  try {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: new URL(HOME_PATH, window.location.href).toString() },
    });
    if (error) throw error;
  } catch (err) {
    showError(err?.message || "Google sign-in failed.");
  }
});

form.addEventListener("submit", handleSubmit);

// If already signed in, bounce straight to /home.
(async () => {
  const { data } = await supabase.auth.getSession();
  if (data?.session) window.location.href = HOME_PATH;
})();

applyMode();

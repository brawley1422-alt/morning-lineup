// Password reset completion page. Supabase sends users here with a recovery
// token in the URL hash; the client auto-detects it and establishes a temporary
// session we use to call updateUser({ password }).

import { supabase } from "./session.js";

const form = document.getElementById("reset-form");
const errorBox = document.getElementById("reset-error");
const noticeBox = document.getElementById("reset-notice");
const submitBtn = document.getElementById("reset-submit");
const lede = document.getElementById("reset-lede");

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

// Verify we actually have a recovery session before letting the user submit.
(async () => {
  const { data } = await supabase.auth.getSession();
  if (!data?.session) {
    submitBtn.disabled = true;
    lede.textContent = "This reset link is invalid or has expired. Request a new one from the sign-in page.";
  }
})();

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorBox.hidden = true;
  noticeBox.hidden = true;
  const fd = new FormData(form);
  const password = (fd.get("password") || "").toString();
  const confirm = (fd.get("confirm") || "").toString();

  if (password.length < 6) {
    showError("Password must be at least 6 characters.");
    return;
  }
  if (password !== confirm) {
    showError("Passwords don't match.");
    return;
  }

  submitBtn.disabled = true;
  try {
    const { error } = await supabase.auth.updateUser({ password });
    if (error) throw error;
    showNotice("Password updated. Redirecting to sign in...");
    setTimeout(() => {
      window.location.href = "index.html";
    }, 1400);
  } catch (err) {
    showError(err?.message || "Could not update password.");
    submitBtn.disabled = false;
  }
});

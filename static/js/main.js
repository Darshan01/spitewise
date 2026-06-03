// main.js — shared utilities loaded on every page

function openModal(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.style.display = "flex";
  // Focus the first input inside the modal
  const firstInput = el.querySelector("input, select, textarea");
  if (firstInput) setTimeout(() => firstInput.focus(), 50);
  // Close on backdrop click
  el.addEventListener("click", _backdropClose);
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.style.display = "none";
  el.removeEventListener("click", _backdropClose);
}

function _backdropClose(e) {
  if (e.target === e.currentTarget) closeModal(e.currentTarget.id);
}

// Close modals on Escape key
document.addEventListener("keydown", e => {
  if (e.key !== "Escape") return;
  document.querySelectorAll(".modal-backdrop").forEach(el => {
    if (el.style.display !== "none") closeModal(el.id);
  });
});
"use strict";

document.querySelectorAll("button[data-copy]").forEach((button) => {
  button.addEventListener("click", async () => {
    const field = document.getElementById(button.dataset.copy);
    const status = document.getElementById("copy-status");
    if (!field || !status) return;
    try {
      await navigator.clipboard.writeText(field.value);
      status.textContent = "Copied. Keep the source notes, dates and limitations with the chart.";
    } catch (_error) {
      field.focus();
      field.select();
      status.textContent = "Text selected. Press Control+C or Command+C to copy.";
    }
  });
});

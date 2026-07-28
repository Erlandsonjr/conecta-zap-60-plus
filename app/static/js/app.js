document.querySelectorAll("form[data-confirm]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (!window.confirm(form.dataset.confirm)) {
      event.preventDefault();
    }
  });
});

document.querySelectorAll(".alert").forEach((alert) => {
  alert.setAttribute("tabindex", "-1");
  alert.focus();
});

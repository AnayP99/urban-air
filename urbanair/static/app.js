function trackEvent(eventName, citySlug) {
  fetch("/api/events", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      event_name: eventName,
      city_slug: citySlug || document.body.dataset.citySlug || null,
    }),
  }).catch(() => {});
}

function savedCities() {
  try {
    return JSON.parse(window.localStorage.getItem("urbanair-saved-cities") || "[]");
  } catch (error) {
    return [];
  }
}

function renderSavedCities() {
  document.querySelectorAll(".saved-cities-list").forEach((container) => {
    const items = savedCities();
    if (!items.length) {
      container.innerHTML = `<p class="panel-note">${container.dataset.emptyMessage || "No saved cities yet."}</p>`;
      return;
    }

    container.innerHTML = items
      .map((slug) => {
        const label = slug
          .split("-")
          .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
          .join(" ");
        return `<a class="saved-city-chip" href="/cities/${slug}">${label}</a>`;
      })
      .join("");
  });
}

document.querySelectorAll(".save-city-button").forEach((button) => {
  button.addEventListener("click", () => {
    const slug = button.dataset.city;
    if (!slug) {
      return;
    }
    const current = new Set(JSON.parse(window.localStorage.getItem("urbanair-saved-cities") || "[]"));
    current.add(slug);
    window.localStorage.setItem("urbanair-saved-cities", JSON.stringify(Array.from(current)));
    button.textContent = "Saved";
    renderSavedCities();
    trackEvent("save_city", slug);
  });
});

document.querySelectorAll(".feedback-button").forEach((button) => {
  button.addEventListener("click", () => {
    const feedback = button.dataset.feedback || "unknown";
    trackEvent(`feedback_${feedback}`);
    document.querySelectorAll(".feedback-button").forEach((node) => {
      node.disabled = true;
    });
  });
});

document.querySelectorAll("[data-track-event]").forEach((element) => {
  const eventName = element.getAttribute("data-track-event");
  if (eventName) {
    trackEvent(eventName);
  }
});

const waitlistForm = document.querySelector(".waitlist-form");

if (waitlistForm) {
  waitlistForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const statusNode = waitlistForm.querySelector(".form-status");
    const formData = new FormData(waitlistForm);
    const payload = {
      email: formData.get("email"),
      city_slug: formData.get("city_slug"),
    };

    try {
      const response = await fetch("/api/alerts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error("Unable to save demo signup");
      }
      const body = await response.json();
      if (statusNode) {
        statusNode.textContent = `Demo signup saved locally for ${body.city}.`;
      }
      waitlistForm.reset();
      trackEvent("alert_signup", payload.city_slug);
    } catch (error) {
      if (statusNode) {
        statusNode.textContent = "Something went wrong. Please try again.";
      }
    }
  });
}

renderSavedCities();
trackEvent("page_view");

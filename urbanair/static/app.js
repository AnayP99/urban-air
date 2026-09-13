// app.js — UrbanAir client-side interactions
// This file is loaded as type="module"

// 1. trackEvent
export function trackEvent(eventName, citySlug = null) {
  const payload = {
    event_name: eventName,
    city_slug: citySlug,
    timestamp: new Date().toISOString()
  };
  fetch('/api/events', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  }).catch(() => {
    // Silent fail for telemetry
  });
}

// 2. getSavedCities / setSavedCities
export function getSavedCities() {
  try {
    const saved = localStorage.getItem('urbanair_saved_cities');
    return saved ? JSON.parse(saved) : [];
  } catch (e) {
    console.error('Failed to parse saved cities', e);
    return [];
  }
}

export function setSavedCities(cities) {
  try {
    localStorage.setItem('urbanair_saved_cities', JSON.stringify(cities));
  } catch (e) {
    console.error('Failed to save cities', e);
  }
}

// 3. renderSavedCities
function renderSavedCities() {
  const containers = document.querySelectorAll('.saved-cities-list');
  if (!containers.length) return;

  const savedCities = getSavedCities();

  containers.forEach(container => {
    container.innerHTML = ''; // clear existing
    if (savedCities.length > 0) {
      savedCities.forEach(city => {
        const chip = document.createElement('div');
        chip.className = 'saved-city-chip';

        const link = document.createElement('a');
        link.href = `/cities/${encodeURIComponent(city.slug)}`;
        link.textContent = city.name;

        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.innerHTML = '&times;';
        removeBtn.setAttribute('aria-label', `Remove ${city.name} from saved`);

        removeBtn.addEventListener('click', (e) => {
          e.preventDefault();
          const newCities = getSavedCities().filter(c => c.slug !== city.slug);
          setSavedCities(newCities);
          renderSavedCities(); // re-render
        });

        chip.appendChild(link);
        chip.appendChild(removeBtn);
        container.appendChild(chip);
      });
    } else {
      const emptyMsg = container.getAttribute('data-empty-message') || 'No saved cities yet.';
      const emptyP = document.createElement('p');
      emptyP.className = 'panel-note';
      emptyP.textContent = emptyMsg;
      container.appendChild(emptyP);
    }
  });
}

// Initialize on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
  const body = document.body;
  const currentCitySlug = body.getAttribute('data-city-slug') || null;

  // Auto-track page view
  trackEvent('page_view', currentCitySlug);

  // Initial render of saved cities
  renderSavedCities();

  // 4. Save city button
  const saveBtn = document.querySelector('.save-city-button');
  if (saveBtn) {
    const slug = saveBtn.getAttribute('data-city');
    const name = saveBtn.getAttribute('data-city-name');

    // Check if already saved
    const savedCities = getSavedCities();
    if (savedCities.some(c => c.slug === slug)) {
      saveBtn.textContent = 'Saved ✓';
    }

    saveBtn.addEventListener('click', () => {
      let cities = getSavedCities();
      if (!cities.some(c => c.slug === slug)) {
        cities.push({ slug, name });
        setSavedCities(cities);
        saveBtn.textContent = 'Saved ✓';
        trackEvent('city_saved', slug);
        renderSavedCities();
      }
    });
  }

  // 5. Feedback buttons
  const feedbackBtns = document.querySelectorAll('.feedback-button');
  const feedbackStatus = document.getElementById('feedback-status');

  feedbackBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      btn.classList.add('pressed');
      setTimeout(() => btn.classList.remove('pressed'), 200);

      const type = btn.getAttribute('data-feedback');
      trackEvent(`feedback_${type}`, currentCitySlug);

      feedbackBtns.forEach(b => b.disabled = true);
      if (feedbackStatus) {
        feedbackStatus.textContent = "Thanks for the feedback!";
      }
    });
  });

  // 6. Waitlist form
  const form = document.querySelector('.waitlist-form');
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const statusEl = form.querySelector('.form-status');
      const submitBtn = form.querySelector('button[type="submit"]');

      const emailInput = form.querySelector('input[name="email"]');
      const citySelect = form.querySelector('select[name="city_slug"]');
      const email = emailInput ? emailInput.value.trim() : '';
      const city_slug = citySelect ? citySelect.value : '';

      if (!email || !city_slug) return;

      submitBtn.disabled = true;
      submitBtn.textContent = 'Saving...';

      try {
        const response = await fetch('/api/alerts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, city_slug })
        });

        if (response.ok) {
          statusEl.textContent = 'Saved successfully for this demo.';
          statusEl.style.color = 'var(--aqi-good)';
          trackEvent('alert_signup', city_slug);
          form.reset();
        } else {
          const errData = await response.json().catch(() => ({}));
          statusEl.textContent = errData.detail || 'An error occurred. Please check your email and try again.';
          statusEl.style.color = 'var(--aqi-unhealthy)';
        }
      } catch (err) {
        statusEl.textContent = 'Network error. Please try again.';
        statusEl.style.color = 'var(--aqi-unhealthy)';
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Save demo signup';
      }
    });
  }

  // 7. City search with auto-complete and keyboard navigation
  const citySearch = document.getElementById('city-search');
  const datalist = document.getElementById('city-list');

  function navigateToCity(query) {
    if (!query || !datalist) return false;
    const normalized = query.trim().toLowerCase();
    const options = Array.from(datalist.options);

    // Exact match on option value (city name) or option data-slug
    const match = options.find(opt => {
      const name = opt.value.trim().toLowerCase();
      const slug = (opt.getAttribute('data-slug') || '').toLowerCase();
      return name === normalized || slug === normalized;
    });

    if (match) {
      const targetSlug = match.getAttribute('data-slug') || match.value.trim().toLowerCase();
      window.location.href = `/cities/${encodeURIComponent(targetSlug)}`;
      return true;
    }
    return false;
  }

  if (citySearch) {
    // Navigate immediately on datalist selection
    citySearch.addEventListener('input', (e) => {
      navigateToCity(e.target.value);
    });

    // Navigate on Enter keypress
    citySearch.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        navigateToCity(citySearch.value);
      }
    });
  }
});

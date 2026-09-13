// chart.js — UrbanAir 24-hour outdoor timeline chart
// Loaded as type="module"

document.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('timelineChart');
  if (!canvas) return;

  const dataScript = document.getElementById('timeline-data');
  if (!dataScript) return;

  if (typeof Chart === 'undefined') {
    console.warn('Chart.js library is not loaded');
    return;
  }

  let timelineData;
  try {
    timelineData = JSON.parse(dataScript.textContent);
  } catch (e) {
    console.error('Failed to parse timeline data', e);
    return;
  }

  if (!Array.isArray(timelineData) || timelineData.length === 0) {
    return;
  }

  function getThemeColors() {
    const isDarkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    return {
      tickColor: isDarkMode ? '#7da893' : '#5f776e',
      gridColor: isDarkMode ? 'rgba(255,255,255,0.07)' : 'rgba(22, 53, 44, 0.05)'
    };
  }

  const theme = getThemeColors();
  const labels = timelineData.map(d => d.label);
  const scores = timelineData.map(d => d.score);

  const backgroundColors = timelineData.map(d => {
    if (d.score >= 7) return 'rgba(42, 157, 92, 0.82)'; // Good
    if (d.score >= 4.5) return 'rgba(200, 135, 10, 0.82)'; // Moderate
    return 'rgba(192, 57, 43, 0.82)'; // Poor
  });

  const borderColors = timelineData.map(d => {
    if (d.is_best) return '#5ecb8b';
    if (d.is_worst) return '#e88070';
    return 'transparent';
  });

  const borderWidths = timelineData.map(d => {
    if (d.is_best || d.is_worst) return 3;
    return 0;
  });

  const config = {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Outdoor Score',
        data: scores,
        backgroundColor: backgroundColors,
        borderColor: borderColors,
        borderWidth: borderWidths,
        borderRadius: 4,
        borderSkipped: false
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 600,
        easing: 'easeOutQuart'
      },
      scales: {
        y: {
          beginAtZero: true,
          max: 10,
          grid: { color: theme.gridColor },
          ticks: { color: theme.tickColor }
        },
        x: {
          grid: { display: false },
          ticks: { color: theme.tickColor, maxRotation: 0 }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function(context) {
              const d = timelineData[context.dataIndex];
              if (!d) return `Outdoor Score: ${context.parsed.y}/10`;
              return [
                `Outdoor Score: ${Number(d.score).toFixed(1)}/10`,
                `AQI: ${Number(d.aqi).toFixed(0)}`,
                `Temp: ${Number(d.temperature).toFixed(0)}°C`,
                `Humidity: ${Number(d.humidity).toFixed(0)}%`
              ];
            }
          }
        },
        annotation: {
          annotations: {
            lineGood: {
              type: 'line',
              yMin: 7,
              yMax: 7,
              borderColor: 'rgba(42, 157, 92, 0.4)',
              borderWidth: 1,
              borderDash: [5, 5]
            },
            lineModerate: {
              type: 'line',
              yMin: 4.5,
              yMax: 4.5,
              borderColor: 'rgba(200, 135, 10, 0.4)',
              borderWidth: 1,
              borderDash: [5, 5]
            }
          }
        }
      }
    }
  };

  // If annotation plugin is not registered, remove annotation config to avoid errors
  try {
    if (!Chart.registry || !Chart.registry.plugins || !Chart.registry.plugins.get('annotation')) {
      delete config.options.plugins.annotation;
    }
  } catch {
    delete config.options.plugins.annotation;
  }

  const chartInstance = new Chart(canvas, config);

  // Dynamic theme update when system theme changes
  if (window.matchMedia) {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    mediaQuery.addEventListener('change', () => {
      const updatedTheme = getThemeColors();
      if (chartInstance.options.scales.y) {
        chartInstance.options.scales.y.grid.color = updatedTheme.gridColor;
        chartInstance.options.scales.y.ticks.color = updatedTheme.tickColor;
      }
      if (chartInstance.options.scales.x) {
        chartInstance.options.scales.x.ticks.color = updatedTheme.tickColor;
      }
      chartInstance.update();
    });
  }
});

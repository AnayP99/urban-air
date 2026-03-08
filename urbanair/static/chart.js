const timelineDataNode = document.getElementById("timeline-data");

if (timelineDataNode) {
  const timelineData = JSON.parse(timelineDataNode.textContent);
  const labels = timelineData.map((item) => item.label);
  const scores = timelineData.map((item) => item.score);
  const backgroundColors = timelineData.map((item) => {
    if (item.category === "good") {
      return "rgba(43, 214, 123, 0.75)";
    }
    if (item.category === "moderate") {
      return "rgba(240, 188, 66, 0.75)";
    }
    return "rgba(242, 95, 92, 0.78)";
  });
  const borderColors = timelineData.map((item) => {
    if (item.is_best) {
      return "#bfffd2";
    }
    if (item.is_worst) {
      return "#ffc3c3";
    }
    return "rgba(255, 255, 255, 0.16)";
  });
  const borderWidths = timelineData.map((item) => {
    if (item.is_best || item.is_worst) {
      return 3;
    }
    return 1;
  });

  const canvas = document.getElementById("timelineChart");

  new Chart(canvas, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Outdoor Score",
          data: scores,
          backgroundColor: backgroundColors,
          borderColor: borderColors,
          borderWidth: borderWidths,
          borderRadius: 8,
          borderSkipped: false,
          barPercentage: 0.92,
          categoryPercentage: 0.94,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 650,
      },
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          callbacks: {
            label(context) {
              const point = timelineData[context.dataIndex];
              let message = `Outdoor Score: ${context.parsed.y}/10`;
              if (point.is_best) {
                message += " | Best window";
              } else if (point.is_worst) {
                message += " | Time to avoid";
              }
              return message;
            },
          },
        },
      },
      scales: {
        x: {
          grid: {
            display: false,
          },
          ticks: {
            color: "#97a9bc",
            maxRotation: 0,
            autoSkip: true,
            maxTicksLimit: 12,
          },
        },
        y: {
          min: 0,
          max: 10,
          grid: {
            color: "rgba(255, 255, 255, 0.08)",
          },
          ticks: {
            color: "#97a9bc",
            stepSize: 2,
          },
          title: {
            display: true,
            text: "Outdoor Score",
            color: "#cbd9e7",
          },
        },
      },
    },
  });
}

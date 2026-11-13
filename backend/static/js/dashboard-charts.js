/**
 * dashboard-charts.js - Renderização dinâmica e assíncrona dos gráficos de gestão com Chart.js.
 *
 * Atende às diretrizes do Projeto Integrador II:
 * - Consumo assíncrono da API REST (/api/v1/dashboard/metrics/)
 * - Gráfico de Donut: Billability Rate (% de horas faturáveis vs não-faturáveis)
 * - Gráfico de Barras: Burn Rate por Projeto (% orçamento consumido com alertas de cor)
 * - Acessibilidade WCAG 2.1 AA com textos alternativos e compatibilidade com leitores de tela
 */

(function () {
    "use strict";

    let billabilityChart = null;
    let burnRateChart = null;

    async function initDashboardCharts() {
        const billabilityCanvas = document.getElementById("chart-billability");
        const burnRateCanvas = document.getElementById("chart-burn-rate");

        // Se a página não tiver os canvases de gráficos, encerra silenciosamente
        if (!billabilityCanvas && !burnRateCanvas) {
            return;
        }

        // Aguarda carregamento do Chart.js caso carregado assincronamente
        if (typeof Chart === "undefined") {
            console.warn("[DashboardCharts] Chart.js ainda não carregado. Tentando novamente em 300ms...");
            setTimeout(initDashboardCharts, 300);
            return;
        }

        try {
            const response = await fetch("/api/v1/dashboard/metrics/", {
                headers: {
                    "Accept": "application/json",
                    "X-Requested-With": "XMLHttpRequest"
                }
            });

            if (!response.ok) {
                throw new Error(`Erro HTTP ${response.status} ao carregar métricas.`);
            }

            const data = await response.json();
            if (!data.success || !data.charts) {
                throw new Error("Payload de métricas incompleto.");
            }

            renderBillabilityChart(billabilityCanvas, data.charts.billability);
            if (burnRateCanvas && data.charts.projects_burn_rate) {
                renderBurnRateChart(burnRateCanvas, data.charts.projects_burn_rate);
            }
        } catch (error) {
            console.error("[DashboardCharts] Falha ao renderizar gráficos:", error);
            showChartFallback(billabilityCanvas, "Não foi possível carregar o gráfico de Billability.");
            showChartFallback(burnRateCanvas, "Não foi possível carregar o gráfico de Burn Rate.");
        }
    }

    function renderBillabilityChart(canvas, billabilityData) {
        if (!canvas) return;

        const billable = Number(billabilityData.billable_percent) || 0;
        const nonBillable = Number(billabilityData.non_billable_percent) || 0;
        const billableHours = Number(billabilityData.billable_hours) || 0;
        const nonBillableHours = Number(billabilityData.non_billable_hours) || 0;

        if (billabilityChart) {
            billabilityChart.destroy();
        }

        const ctx = canvas.getContext("2d");
        billabilityChart = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: ["Horas Faturáveis", "Horas Não-Faturáveis"],
                datasets: [{
                    data: [billable, nonBillable],
                    backgroundColor: ["#0284c7", "#94a3b8"],
                    hoverBackgroundColor: ["#0369a1", "#64748b"],
                    borderWidth: 2,
                    borderColor: "#ffffff"
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            boxWidth: 14,
                            padding: 16,
                            font: { size: 13, family: "inherit" }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const label = context.label || "";
                                const val = context.parsed || 0;
                                const hours = context.dataIndex === 0 ? billableHours : nonBillableHours;
                                return `${label}: ${val.toFixed(1)}% (${hours.toFixed(1)}h)`;
                            }
                        }
                    }
                },
                cutout: "68%"
            }
        });

        // Acessibilidade WCAG: Atualizar texto alternativo
        const altText = `Gráfico de rosca: ${billable.toFixed(1)}% de horas faturáveis (${billableHours.toFixed(1)}h) e ${nonBillable.toFixed(1)}% não-faturáveis (${nonBillableHours.toFixed(1)}h).`;
        canvas.setAttribute("aria-label", altText);
        const fallbackText = canvas.querySelector(".sr-only-chart-desc");
        if (fallbackText) {
            fallbackText.textContent = altText;
        }
    }

    function renderBurnRateChart(canvas, projectsData) {
        if (!canvas) return;

        const labels = projectsData.labels || [];
        const burnRates = projectsData.burn_rates || [];
        const profitMargins = projectsData.profit_margins || [];
        const healthStatuses = projectsData.health_statuses || [];

        if (burnRateChart) {
            burnRateChart.destroy();
        }

        // Cores semânticas conforme o limiar de risco
        const burnRateColors = burnRates.map(rate => {
            if (rate >= 90) return "#ef4444"; // Crítico (Vermelho)
            if (rate >= 70) return "#f59e0b"; // Atenção (Amarelo/Laranja)
            return "#10b981"; // Saudável (Verde)
        });

        const ctx = canvas.getContext("2d");
        burnRateChart = new Chart(ctx, {
            type: "bar",
            data: {
                labels: labels.length > 0 ? labels : ["Nenhum projeto"],
                datasets: [
                    {
                        label: "Burn Rate (% Orçamento Consumido)",
                        data: burnRates.length > 0 ? burnRates : [0],
                        backgroundColor: burnRateColors,
                        borderRadius: 6,
                        maxBarThickness: 42
                    },
                    {
                        label: "Margem de Lucro (%)",
                        data: profitMargins.length > 0 ? profitMargins : [0],
                        backgroundColor: "#3b82f6",
                        borderRadius: 6,
                        maxBarThickness: 42
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function (val) {
                                return val + "%";
                            }
                        },
                        grid: {
                            color: "rgba(0, 0, 0, 0.06)"
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            boxWidth: 14,
                            padding: 16,
                            font: { size: 13, family: "inherit" }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            afterLabel: function (context) {
                                if (context.datasetIndex === 0) {
                                    const status = healthStatuses[context.dataIndex] || "Normal";
                                    return `Status de Saúde: ${status}`;
                                }
                                return "";
                            }
                        }
                    }
                }
            }
        });

        // Acessibilidade WCAG
        const altText = `Gráfico de barras de Burn Rate e Margem de Lucro para ${labels.length} projetos ativos.`;
        canvas.setAttribute("aria-label", altText);
        const fallbackText = canvas.querySelector(".sr-only-chart-desc");
        if (fallbackText) {
            fallbackText.textContent = altText;
        }
    }

    function showChartFallback(canvas, message) {
        if (!canvas) return;
        const parent = canvas.parentElement;
        if (parent) {
            const errorMsg = document.createElement("p");
            errorMsg.className = "chart-fallback-message muted-text";
            errorMsg.style.textAlign = "center";
            errorMsg.style.padding = "2rem 1rem";
            errorMsg.textContent = message;
            canvas.replaceWith(errorMsg);
        }
    }

    // Inicialização ao carregar o DOM
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initDashboardCharts);
    } else {
        initDashboardCharts();
    }
})();

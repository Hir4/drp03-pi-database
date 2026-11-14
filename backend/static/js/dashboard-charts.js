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
    let weeklyChart = null;

    // Cores lidas das variáveis CSS: os gráficos acompanham o tema claro/escuro.
    function themeColor(name, fallback) {
        const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
        return value || fallback;
    }

    function gridColor() {
        return document.documentElement.dataset.theme === "dark"
            ? "rgba(231, 235, 247, 0.1)"
            : "rgba(26, 35, 64, 0.08)";
    }
    // Respeita a preferência do sistema por menos movimento (WCAG 2.3.3).
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reducedMotion && typeof Chart !== "undefined") {
        Chart.defaults.animation = false;
    }

    async function initDashboardCharts() {
        const billabilityCanvas = document.getElementById("chart-billability");
        const burnRateCanvas = document.getElementById("chart-burn-rate");
        const weeklyCanvas = document.getElementById("chart-weekly-hours");

        // Se a página não tiver os canvases de gráficos, encerra silenciosamente
        if (!billabilityCanvas && !burnRateCanvas && !weeklyCanvas) {
            return;
        }

        // Aguarda carregamento do Chart.js caso carregado assincronamente
        if (typeof Chart === "undefined") {
            console.warn("[DashboardCharts] Chart.js ainda não carregado. Tentando novamente em 300ms...");
            setTimeout(initDashboardCharts, 300);
            return;
        }

        Chart.defaults.color = themeColor("--muted", "#5f6c8c");
        Chart.defaults.borderColor = gridColor();

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
            if (weeklyCanvas && data.charts.weekly_hours) {
                renderWeeklyHoursChart(weeklyCanvas, data.charts.weekly_hours);
            }
        } catch (error) {
            console.error("[DashboardCharts] Falha ao renderizar gráficos:", error);
            showChartFallback(billabilityCanvas, "Não foi possível carregar o gráfico de Billability.");
            showChartFallback(burnRateCanvas, "Não foi possível carregar o gráfico de Burn Rate.");
            showChartFallback(weeklyCanvas, "Não foi possível carregar o gráfico de horas semanais.");
        }
    }

    // Gráfico do consultor: horas por semana (faturáveis x não faturáveis) com a meta semanal.
    function renderWeeklyHoursChart(canvas, weekly) {
        const number = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });
        const totals = weekly.labels.map((_, index) => weekly.billable_hours[index] + weekly.non_billable_hours[index]);
        const existingWeeklyChart = Chart.getChart(canvas);
        if (existingWeeklyChart) {
            existingWeeklyChart.destroy();
        }
        weeklyChart = new Chart(canvas.getContext("2d"), {
            type: "bar",
            data: {
                labels: weekly.labels,
                datasets: [
                    {
                        type: "line",
                        label: `Meta (${weekly.target}h)`,
                        data: weekly.labels.map(() => weekly.target),
                        borderColor: themeColor("--muted", "#5f6c8c"),
                        borderDash: [6, 6],
                        borderWidth: 1.5,
                        pointRadius: 0,
                        order: 0
                    },
                    { label: "Faturáveis", data: weekly.billable_hours, backgroundColor: themeColor("--primary", "#2952e3"), borderRadius: 4, order: 1 },
                    { label: "Não faturáveis", data: weekly.non_billable_hours, backgroundColor: "#94a3b8", borderRadius: 4, order: 1 }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: reducedMotion ? false : undefined,
                scales: {
                    x: { stacked: true, grid: { display: false }, title: { display: true, text: "Semana (início)" } },
                    y: { stacked: true, beginAtZero: true, suggestedMax: weekly.target + 5, title: { display: true, text: "Horas" } }
                },
                plugins: {
                    legend: { position: "bottom", labels: { boxWidth: 14, padding: 16 } },
                    tooltip: {
                        callbacks: {
                            label: (context) => `${context.dataset.label}: ${number.format(context.parsed.y)}h`,
                            footer: (items) => `Total: ${number.format(totals[items[0].dataIndex])}h`
                        }
                    }
                }
            }
        });

        const lastIndex = totals.length - 1;
        const average = totals.reduce((sum, value) => sum + value, 0) / (totals.length || 1);
        canvas.setAttribute(
            "aria-label",
            `Suas horas por semana nas últimas ${totals.length} semanas: média de ${number.format(average)}h; ` +
            `semana atual com ${number.format(totals[lastIndex] || 0)}h de uma meta de ${weekly.target}h.`
        );
    }

    function renderBillabilityChart(canvas, billabilityData) {
        if (!canvas) return;

        const billable = Number(billabilityData.billable_percent) || 0;
        const nonBillable = Number(billabilityData.non_billable_percent) || 0;
        const billableHours = Number(billabilityData.billable_hours) || 0;
        const nonBillableHours = Number(billabilityData.non_billable_hours) || 0;

        const existingBillabilityChart = Chart.getChart(canvas);
        if (existingBillabilityChart) {
            existingBillabilityChart.destroy();
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
                    borderColor: themeColor("--surface", "#ffffff")
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

        const existingBurnRateChart = Chart.getChart(canvas);
        if (existingBurnRateChart) {
            existingBurnRateChart.destroy();
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
                            color: gridColor()
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

    // Ao trocar o tema, redesenha os gráficos com as novas cores.
    document.addEventListener("fcn:themechange", initDashboardCharts);

    // Inicialização ao carregar o DOM
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initDashboardCharts);
    } else {
        initDashboardCharts();
    }
})();

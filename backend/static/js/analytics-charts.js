/**
 * analytics-charts.js - Gráficos da tela de Análises e do relatório para PDF (Chart.js).
 *
 * - Consome de forma assíncrona a API /api/v1/analytics/ com os mesmos filtros da página.
 * - Cada gráfico recebe um texto alternativo (aria-label) com o resumo dos dados,
 *   e a página mantém uma tabela equivalente para leitores de tela (WCAG 2.1).
 * - No relatório (data-report="1"), desativa animações e, com data-autoprint="1",
 *   abre a janela de impressão quando os gráficos terminam de desenhar.
 */

(function () {
    "use strict";

    const COLORS = {
        primary: "#2952e3",
        muted: "#94a3b8",
        success: "#1d8f5f",
        warning: "#c68317",
        danger: "#cb3a54",
        grid: "rgba(26, 35, 64, 0.08)"
    };
    const RISK_COLORS = { ok: COLORS.success, warning: COLORS.warning, high: COLORS.danger };

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

    function applyTheme() {
        COLORS.primary = themeColor("--primary", "#2952e3");
        COLORS.success = themeColor("--success", "#1d8f5f");
        COLORS.warning = themeColor("--warning", "#c68317");
        COLORS.danger = themeColor("--danger", "#cb3a54");
        COLORS.grid = gridColor();
        RISK_COLORS.ok = COLORS.success;
        RISK_COLORS.warning = COLORS.warning;
        RISK_COLORS.high = COLORS.danger;
        Chart.defaults.color = themeColor("--muted", "#5f6c8c");
    }
    const RISK_LABELS = { ok: "No ritmo", warning: "Atenção", high: "Em risco" };
    // Formas diferentes por situação: a leitura não depende só da cor (WCAG 1.4.1).
    const RISK_SHAPES = { ok: "circle", warning: "rectRot", high: "triangle" };
    const REDUCED_MOTION = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const number = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });
    const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
    const charts = [];

    function baseOptions(isReport) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            animation: isReport || REDUCED_MOTION ? false : { duration: 400 },
            plugins: {
                legend: {
                    position: "bottom",
                    labels: { boxWidth: 14, padding: 14, font: { size: 12 }, usePointStyle: true }
                }
            }
        };
    }

    function getCanvas(id) {
        return document.getElementById(id);
    }

    function describe(canvas, text) {
        if (canvas) {
            canvas.setAttribute("aria-label", text);
        }
    }

    function showMessage(canvas, message) {
        if (!canvas || !canvas.parentElement) return;
        const paragraph = document.createElement("p");
        paragraph.className = "chart-fallback-message muted-text";
        paragraph.textContent = message;
        canvas.parentElement.replaceChildren(paragraph);
    }

    function fitHeight(canvas, rows) {
        // Gráficos de barras horizontais crescem conforme o número de linhas.
        if (canvas && canvas.parentElement) {
            canvas.parentElement.style.height = Math.max(280, rows * 34 + 90) + "px";
        }
    }

    // Libera o gráfico que já estiver no canvas (ex.: troca de tema durante o carregamento).
    function createChart(canvas, config) {
        const existing = Chart.getChart(canvas);
        if (existing) existing.destroy();
        return new Chart(canvas, config);
    }

    function register(chart) {
        charts.push(chart);
        return chart;
    }

    function renderHoursTrend(trend, isReport) {
        const canvas = getCanvas("chart-hours-trend");
        if (!canvas) return;
        if (!trend.labels.length) {
            showMessage(canvas, "Nenhum lançamento no período escolhido.");
            return;
        }

        const options = baseOptions(isReport);
        options.scales = {
            x: { stacked: true, grid: { display: false } },
            y: {
                stacked: true,
                beginAtZero: true,
                title: { display: true, text: "Horas" },
                grid: { color: COLORS.grid }
            },
            y1: {
                position: "right",
                min: 0,
                max: 100,
                grid: { drawOnChartArea: false },
                ticks: { callback: (value) => value + "%" },
                title: { display: true, text: "Billability" }
            }
        };
        options.plugins.tooltip = {
            callbacks: {
                label: (context) => context.dataset.yAxisID === "y1"
                    ? `Billability: ${number.format(context.parsed.y)}%`
                    : `${context.dataset.label}: ${number.format(context.parsed.y)}h`
            }
        };

        register(createChart(canvas, {
            type: "bar",
            data: {
                labels: trend.labels,
                datasets: [
                    { type: "line", label: "Billability", data: trend.billability, yAxisID: "y1", borderColor: COLORS.success, backgroundColor: COLORS.success, tension: 0.3, pointRadius: 3, clip: false, order: 0 },
                    { label: "Horas faturáveis", data: trend.billable_hours, backgroundColor: COLORS.primary, borderRadius: 4, order: 1 },
                    { label: "Horas não faturáveis", data: trend.non_billable_hours, backgroundColor: COLORS.muted, borderRadius: 4, order: 1 }
                ]
            },
            options: options
        }));

        const total = trend.billable_hours.reduce((a, b) => a + b, 0) + trend.non_billable_hours.reduce((a, b) => a + b, 0);
        const unit = trend.granularity === "month" ? "mês" : "semana";
        describe(canvas, `Horas lançadas por ${unit}, de ${trend.labels[0]} a ${trend.labels[trend.labels.length - 1]}: total de ${number.format(total)} horas. Os valores detalhados estão na tabela abaixo do gráfico.`);
    }

    function renderProjectRisk(rows, isReport) {
        const canvas = getCanvas("chart-project-risk");
        if (!canvas) return;
        if (!rows.length) {
            showMessage(canvas, "Nenhum projeto ativo para os filtros escolhidos.");
            return;
        }

        const maxBurn = Math.max(100, ...rows.map((row) => row.burn_rate));
        const datasets = ["high", "warning", "ok"]
            .map((level) => ({
                type: "scatter",
                label: RISK_LABELS[level],
                data: rows.filter((row) => row.risk_level === level).map((row) => ({ x: row.progress, y: row.burn_rate, project: row.project })),
                backgroundColor: RISK_COLORS[level],
                pointStyle: RISK_SHAPES[level],
                pointRadius: 7,
                pointHoverRadius: 9,
                clip: false
            }))
            .filter((dataset) => dataset.data.length);
        datasets.push({
            type: "line",
            label: "Ritmo ideal",
            data: [{ x: 0, y: 0 }, { x: 100, y: 100 }],
            borderColor: COLORS.muted,
            borderDash: [6, 6],
            borderWidth: 1.5,
            pointRadius: 0,
            fill: false
        });

        const options = baseOptions(isReport);
        options.scales = {
            x: { type: "linear", min: 0, max: 100, title: { display: true, text: "Tarefas concluídas (%)" }, grid: { color: COLORS.grid } },
            y: { min: 0, suggestedMax: Math.ceil(maxBurn / 10) * 10, title: { display: true, text: "Orçamento consumido (%)" }, grid: { color: COLORS.grid } }
        };
        options.plugins.tooltip = {
            callbacks: {
                label: (context) => context.raw.project
                    ? `${context.raw.project}: ${number.format(context.raw.y)}% do orçamento, ${number.format(context.raw.x)}% das tarefas`
                    : "Ritmo ideal (gasto igual ao avanço)"
            }
        };

        register(createChart(canvas, { type: "scatter", data: { datasets: datasets }, options: options }));

        const atRisk = rows.filter((row) => row.risk_level === "high").map((row) => row.project);
        describe(canvas, `Risco de ${rows.length} projetos. ${atRisk.length ? "Em risco: " + atRisk.join(", ") + "." : "Nenhum projeto em risco."} Detalhes na tabela abaixo do gráfico.`);
    }

    function renderEstimateActual(rows, isReport) {
        const canvas = getCanvas("chart-estimate-actual");
        if (!canvas) return;
        if (!rows.length) {
            showMessage(canvas, "Nenhuma tarefa com estimativa ou horas lançadas.");
            return;
        }

        const top = rows.slice(0, 10);
        fitHeight(canvas, top.length);
        const options = baseOptions(isReport);
        options.indexAxis = "y";
        options.scales = {
            x: { beginAtZero: true, title: { display: true, text: "Horas" }, grid: { color: COLORS.grid } },
            y: { grid: { display: false } }
        };
        options.plugins.tooltip = {
            callbacks: {
                label: (context) => `${context.dataset.label}: ${number.format(context.parsed.x)}h`,
                afterBody: (items) => {
                    const row = top[items[0].dataIndex];
                    return row.variance_percent === null ? row.status : `Variação: ${number.format(row.variance_percent)}%`;
                }
            }
        };

        register(createChart(canvas, {
            type: "bar",
            data: {
                labels: top.map((row) => row.project),
                datasets: [
                    { label: "Estimado", data: top.map((row) => row.estimated_hours), backgroundColor: COLORS.muted, borderRadius: 4 },
                    { label: "Realizado", data: top.map((row) => row.actual_hours), backgroundColor: top.map((row) => row.variance_percent > 0 ? COLORS.danger : COLORS.primary), borderRadius: 4 }
                ]
            },
            options: options
        }));

        const over = rows.filter((row) => row.variance_percent > 0).length;
        describe(canvas, `Horas estimadas e realizadas de ${rows.length} projetos; ${over} acima da estimativa. Detalhes na tabela abaixo do gráfico.`);
    }

    function renderTeamLoad(rows, isReport) {
        const canvas = getCanvas("chart-team-load");
        if (!canvas) return;
        if (!rows.length) {
            showMessage(canvas, "Nenhuma hora lançada no período escolhido.");
            return;
        }

        fitHeight(canvas, rows.length);
        const options = baseOptions(isReport);
        options.indexAxis = "y";
        options.scales = {
            x: { stacked: true, beginAtZero: true, title: { display: true, text: "Horas" }, grid: { color: COLORS.grid } },
            y: { stacked: true, grid: { display: false } }
        };
        options.plugins.tooltip = {
            callbacks: {
                label: (context) => `${context.dataset.label}: ${number.format(context.parsed.x)}h`,
                afterBody: (items) => `Billability: ${number.format(rows[items[0].dataIndex].billability)}%`
            }
        };

        register(createChart(canvas, {
            type: "bar",
            data: {
                labels: rows.map((row) => row.name),
                datasets: [
                    { label: "Faturáveis", data: rows.map((row) => row.billable_hours), backgroundColor: COLORS.primary, borderRadius: 4 },
                    { label: "Não faturáveis", data: rows.map((row) => row.non_billable_hours), backgroundColor: COLORS.muted, borderRadius: 4 }
                ]
            },
            options: options
        }));

        const idle = rows.filter((row) => row.total_hours === 0).length;
        describe(canvas, `Horas de ${rows.length} pessoas no período${idle ? `; ${idle} sem lançamentos` : ""}. Detalhes na tabela abaixo do gráfico.`);
    }

    function renderClientProfit(rows, isReport) {
        const canvas = getCanvas("chart-client-profit");
        if (!canvas) return;
        if (!rows.length) {
            showMessage(canvas, "Nenhum cliente para os filtros escolhidos.");
            return;
        }

        const options = baseOptions(isReport);
        options.scales = {
            x: { grid: { display: false } },
            y: { beginAtZero: true, ticks: { callback: (value) => money.format(value) }, grid: { color: COLORS.grid } }
        };
        options.plugins.tooltip = {
            callbacks: {
                label: (context) => `${context.dataset.label}: ${money.format(context.parsed.y)}`,
                afterBody: (items) => `Margem: ${number.format(rows[items[0].dataIndex].margin_percent)}%`
            }
        };

        register(createChart(canvas, {
            type: "bar",
            data: {
                labels: rows.map((row) => row.client),
                datasets: [
                    { label: "Orçamento", data: rows.map((row) => row.budget), backgroundColor: COLORS.muted, borderRadius: 4 },
                    { label: "Custo interno", data: rows.map((row) => row.internal_cost), backgroundColor: rows.map((row) => row.margin_percent < 25 ? COLORS.danger : COLORS.primary), borderRadius: 4 }
                ]
            },
            options: options
        }));

        const lowest = rows[0];
        describe(canvas, `Orçamento e custo interno de ${rows.length} clientes. Menor margem: ${lowest.client}, com ${number.format(lowest.margin_percent)}%. Detalhes na tabela abaixo do gráfico.`);
    }

    function resizeAll() {
        charts.forEach((chart) => chart.resize());
    }

    function bindPrintButton() {
        const button = document.getElementById("report-print-button");
        if (button) {
            button.addEventListener("click", () => window.print());
        }
    }

    async function init() {
        const root = document.getElementById("analytics-root");
        if (!root) return;
        const isReport = root.dataset.report === "1";
        bindPrintButton();

        const canvases = root.querySelectorAll("canvas");
        if (typeof Chart === "undefined") {
            canvases.forEach((canvas) => showMessage(canvas, "Não foi possível carregar os gráficos. Os dados continuam disponíveis na tabela."));
            return;
        }
        Chart.defaults.font.family = "Inter, system-ui, sans-serif";
        applyTheme();

        try {
            const response = await fetch(root.dataset.apiUrl, {
                credentials: "same-origin",
                headers: { "Accept": "application/json", "X-Requested-With": "XMLHttpRequest" }
            });
            if (!response.ok) {
                throw new Error(`Erro HTTP ${response.status} ao carregar a análise.`);
            }
            const data = await response.json();
            if (!data.success) {
                throw new Error("Resposta da análise incompleta.");
            }

            renderHoursTrend(data.hours_trend, isReport);
            renderProjectRisk(data.project_risk, isReport);
            renderEstimateActual(data.estimate_vs_actual, isReport);
            renderTeamLoad(data.team_load, isReport);
            renderClientProfit(data.client_profitability, isReport);
            root.dataset.chartsReady = "1";

            if (isReport && root.dataset.autoprint === "1") {
                window.setTimeout(() => window.print(), 400);
            }
        } catch (error) {
            console.error("[AnalyticsCharts]", error);
            canvases.forEach((canvas) => showMessage(canvas, "Não foi possível carregar o gráfico. Os dados continuam disponíveis na tabela."));
        }
    }

    // O Chart.js não redimensiona sozinho para a área de impressão.
    document.addEventListener("fcn:themechange", () => {
        charts.splice(0).forEach((chart) => chart.destroy());
        init();
    });
    window.addEventListener("beforeprint", resizeAll);
    window.addEventListener("afterprint", resizeAll);

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();

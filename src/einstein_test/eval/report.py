"""Render dos relatórios de avaliação (Markdown, HTML, JSON)."""

from __future__ import annotations

import html
import json


def render_report(report, fmt: str = "md") -> str:
    fmt = fmt.lower()
    if fmt == "json":
        return json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
    if fmt == "html":
        return _render_html(report)
    return _render_markdown(report)


def _render_markdown(report) -> str:
    agg = report.aggregates()
    lines = ["# Relatório de avaliação do RAG", ""]
    if agg:
        lines += ["## Agregados", ""]
        lines += ["| Métrica | Valor |", "|---|---|"]
        for k, v in agg.items():
            lines.append(f"| {k} | {v:.3f} |")
        lines += ["", "## Por pergunta", ""]
    lines += [
        "| id | questão | recall@5 | recall@12 | mrr@5 | hit@1 | corr | fidel | cover | sim | ttft(s) | lat(s) | robustez |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in report.results:
        q, m, v = r.question, r.metrics, r.verdict
        lines.append(
            f"| {q.id} | {q.question} | {m.recall_5:.2f} | {m.recall_12:.2f} | "
            f"{m.mrr_5:.2f} | {m.hit_1:.2f} | {v.correctness:.1f} | "
            f"{v.faithfulness:.1f} | {v.coverage:.1f} | {r.similarity:.2f} | "
            f"{r.ttft:.3f} | {r.latency:.3f} | {r.robustness_ok} |"
        )
    return "\n".join(lines) + "\n"


def _render_html(report) -> str:
    escape = html.escape
    rows = "".join(
        f"<tr><td>{escape(r.question.id)}</td><td>{escape(r.question.question)}</td>"
        f"<td>{r.metrics.recall_5:.2f}</td><td>{r.metrics.recall_12:.2f}</td>"
        f"<td>{r.metrics.mrr_5:.2f}</td><td>{r.metrics.hit_1:.2f}</td>"
        f"<td>{r.verdict.correctness:.1f}</td><td>{r.verdict.faithfulness:.1f}</td>"
        f"<td>{r.verdict.coverage:.1f}</td><td>{r.similarity:.2f}</td>"
        f"<td>{r.ttft:.3f}</td><td>{r.latency:.3f}</td>"
        f"<td>{r.robustness_ok}</td></tr>"
        for r in report.results
    )
    agg = report.aggregates()
    agg_html = "<br>".join(f"{escape(k)}: <b>{v:.3f}</b>" for k, v in agg.items()) if agg else ""
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>Eval RAG</title>"
        "<style>body{font-family:sans-serif;margin:2rem}table{border-collapse:collapse;"
        "margin-top:1rem}th,td{border:1px solid #ccc;padding:6px 10px;font-size:14px}"
        "th{background:#f5f5f5}</style></head><body>"
        f"<h1>Relatório de avaliação do RAG</h1><p>{agg_html}</p>"
        f"<table><tr><th>id</th><th>questão</th><th>recall@5</th><th>recall@12</th>"
        "<th>mrr@5</th><th>hit@1</th><th>corr</th><th>fidel</th><th>cover</th>"
        "<th>sim</th><th>ttft(s)</th><th>lat(s)</th><th>robustez</th></tr>"
        f"{rows}</table></body></html>"
    )
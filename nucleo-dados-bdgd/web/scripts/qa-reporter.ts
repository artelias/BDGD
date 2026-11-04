import { appendFileSync } from "node:fs";
import { basename } from "node:path";
import type { Reporter, TestCase, TestResult, TestStep } from "@playwright/test/reporter";

// Append-only: um relatório continua legível se o runner for interrompido.
export default class QaReporter implements Reporter {
  onTestEnd(test: TestCase, result: TestResult) {
    const file = process.env.QA_RESULTADOS;
    if (!file) return;
    const steps: { category: string; title: string; params?: unknown; line?: number }[] = [];
    function collect(step: TestStep) {
      if (step.category === "pw:api" || step.category === "expect") {
        steps.push({ category: step.category, title: step.title, params: step.params, line: step.location?.line });
      }
      step.steps.forEach(collect);
    }
    result.steps.forEach(collect);
    const evidence = result.attachments.filter((a) => a.contentType === "application/json" && a.body).map((a) => ({ name: a.name, data: JSON.parse(a.body!.toString("utf8")) }));
    appendFileSync(file, JSON.stringify({ test: test.title, project: test.parent.project()?.name, spec: basename(test.location.file), line: test.location.line, status: result.status, duration: result.duration, error: result.error?.message, evidence, steps }) + "\n");
  }
}

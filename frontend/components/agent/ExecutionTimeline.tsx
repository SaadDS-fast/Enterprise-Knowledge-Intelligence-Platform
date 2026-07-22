import type { AgentRunDetail } from "@/types";

function displayState(value: string): string {
  return value.replaceAll("_", " ").toLowerCase();
}

export default function ExecutionTimeline({ run }: { run: AgentRunDetail }) {
  const steps = [...run.steps].sort((a, b) => a.step_number - b.step_number);
  if (!steps.length && !run.tool_calls.length) {
    return <div className="empty">No operational activity was returned.</div>;
  }
  return (
    <ol className="timeline" data-testid="execution-timeline" aria-label="Execution timeline">
      {steps.map((step) => {
        const toolCalls = run.tool_calls.filter((tool) => tool.step_id === step.id);
        return (
          <li key={step.id}>
            <div>
              <strong>{displayState(step.state)}</strong>
              <span className={`badge badge-${step.status.toLowerCase()}`}>{step.status}</span>
            </div>
            <p>{step.summary}</p>
            <small>
              {step.duration_ms ?? 0} ms · {new Date(step.created_at).toLocaleString()}
            </small>
            {step.error_code ? <p className="error">{step.error_code}</p> : null}
            {toolCalls.length ? (
              <div className="tool-list">
                {toolCalls.map((tool) => (
                  <span key={tool.id}>
                    {tool.tool_name.replaceAll("_", " ")} · {tool.status}
                    {typeof tool.duration_ms === "number" ? ` · ${tool.duration_ms} ms` : ""}
                  </span>
                ))}
              </div>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}

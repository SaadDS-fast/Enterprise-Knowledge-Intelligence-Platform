import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import EvaluationWorkspace from "./EvaluationWorkspace";

vi.mock("@/lib/api", () => ({
  api: vi.fn(),
}));

import { api } from "@/lib/api";

const mockedApi = vi.mocked(api);

describe("EvaluationWorkspace", () => {
  beforeEach(() => {
    mockedApi.mockReset();
  });

  it("keeps fields after a failed submission without calling form reset", async () => {
    mockedApi.mockResolvedValueOnce([]);
    mockedApi.mockRejectedValueOnce(new Error("Evaluation failed safely"));

    render(<EvaluationWorkspace />);

    await userEvent.type(screen.getByTestId("evaluation-name"), "Demo topic quality check");
    await userEvent.type(screen.getByTestId("evaluation-question"), "What is the demo topic?");
    await userEvent.type(screen.getByTestId("evaluation-answer"), "Functions");
    fireEvent.click(screen.getByTestId("evaluation-submit"));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Evaluation failed safely"));
    expect(screen.getByTestId("evaluation-name")).toHaveValue("Demo topic quality check");
    expect(screen.getByTestId("evaluation-question")).toHaveValue("What is the demo topic?");
    expect(screen.getByTestId("evaluation-answer")).toHaveValue("Functions");
  });

  it("clears fields after successful deterministic evaluation", async () => {
    mockedApi.mockResolvedValueOnce([]);
    mockedApi.mockResolvedValueOnce({});
    mockedApi.mockResolvedValueOnce([
      {
        id: "run-1",
        name: "Demo topic quality check",
        status: "completed",
        metrics_json: { pass_rate: 1, normalized_answer_match: 1, token_f1: 1 },
        config_json: {
          pipeline: "standard_search",
          case_results: [
            {
              question: "What is the demo topic?",
              expected_answer: "Functions",
              actual_answer: "The demo topic is Functions.",
              actual_value: "Functions",
              passed: true,
              normalized_answer_match: true,
              token_f1: 1,
              evidence_support: "SUPPORTED",
              citation_validity: true,
              abstained: false,
              conflict_status: "ANSWER_SUPPORTED",
            },
          ],
        },
        created_at: "2026-07-24T00:00:00Z",
        updated_at: "2026-07-24T00:00:00Z",
      },
    ]);

    render(<EvaluationWorkspace />);

    await userEvent.type(screen.getByTestId("evaluation-name"), "Demo topic quality check");
    await userEvent.type(screen.getByTestId("evaluation-question"), "What is the demo topic?");
    await userEvent.type(screen.getByTestId("evaluation-answer"), "Functions");
    fireEvent.click(screen.getByTestId("evaluation-submit"));

    await waitFor(() => expect(screen.getByText("Demo topic quality check")).toBeInTheDocument());
    expect(screen.getByTestId("evaluation-name")).toHaveValue("");
    expect(screen.getByTestId("evaluation-question")).toHaveValue("");
    expect(screen.getByTestId("evaluation-answer")).toHaveValue("");
    expect(screen.getByText("Pipeline: standard_search")).toBeInTheDocument();
    expect(screen.getByText("PASS")).toBeInTheDocument();
    expect(screen.getByText("Actual answer: The demo topic is Functions.")).toBeInTheDocument();
    expect(screen.getByText("Normalized answer match: yes")).toBeInTheDocument();
    expect(screen.getByText("Token F1: 1.000")).toBeInTheDocument();
    expect(screen.getByText("Evidence support: SUPPORTED")).toBeInTheDocument();
    expect(screen.getByText("Citation validity: valid")).toBeInTheDocument();
  });
});

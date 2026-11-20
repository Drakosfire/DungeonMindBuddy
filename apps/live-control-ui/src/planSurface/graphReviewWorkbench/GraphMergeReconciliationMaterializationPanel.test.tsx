import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { GraphMergeReconciliationMaterializationPanel } from "./GraphMergeReconciliationMaterializationPanel";

it("directs users from retired materialization to governed Graph Review", () => {
  render(
    <GraphMergeReconciliationMaterializationPanel
      campaignId="longmont-c2"
      sessionId="session-23"
    />,
  );

  expect(screen.getByTestId("graph-merge-reconciliation-materialization-panel"))
    .toHaveTextContent(/longmont-c2 \/ session-23 is retired.*HTTP 410/);
  expect(screen.getByText(/Use Graph Review prepare\/commit/)).toBeVisible();
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
});

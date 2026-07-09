import type { SelectedObjectAction, SelectedObjectCardModel } from "./selectedObjectCardModel";

export interface SelectedObjectActionOptions {
  ingestHref?: string;
}

export function buildSelectedObjectActions(
  model: SelectedObjectCardModel,
  options: SelectedObjectActionOptions = {},
): SelectedObjectAction[] {
  const ingestHref = options.ingestHref ?? "/ingest";
  const actions: SelectedObjectAction[] = [];

  for (const intent of model.actionIntents) {
    switch (intent) {
      case "expand":
        actions.push({ id: "expand", label: "Expand details" });
        break;
      case "ingest":
        actions.push({
          id: "ingest",
          label: "Review memory in /ingest",
          href: ingestHref,
        });
        break;
      case "statblock_tool":
        actions.push({ id: "statblock", label: "Open statblock tool" });
        break;
      case "roll": {
        const dice = model.metadata?.dice;
        if (dice) {
          actions.push({
            id: "roll",
            label: `Roll ${dice}`,
            payload: { dice },
          });
        }
        break;
      }
      case "source_preview": {
        const sourcePath = model.sourcePath || model.metadata?.corpusDisplayPath;
        if (sourcePath) {
          actions.push({
            id: "source_preview",
            label: "Show source preview",
            payload: { sourcePath },
          });
        }
        break;
      }
      default:
        break;
    }
  }

  return actions;
}

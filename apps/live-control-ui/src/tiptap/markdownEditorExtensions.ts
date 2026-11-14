import {WorkPlanNode} from "../surface/workPlans/WorkPlanNode";
import {PreparedTableNode} from "../preparedTables/PreparedTableNode";
import type { AnyExtension } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";

import { CalloutNode } from "./extensions/CalloutNode";
import { DECISION_CONSEQUENCE_EXTENSIONS } from "./extensions/DecisionConsequenceNode";
import { GraphNodeReferenceNode } from "./extensions/GraphNodeReferenceNode";
import { PLAN_TABLE_EXTENSIONS } from "./extensions/planTableExtensions";
import { PlayableElementHeadingAttributes } from "./extensions/PlayableElementHeadingAttributes";
import { RunbookReferenceNode } from "./extensions/RunbookReferenceNode";

import { WebSourceLink } from "./extensions/WebSourceLink";

import { MediaImageNode } from "./extensions/MediaImageNode";

export const DEFAULT_MARKDOWN_EDITOR_EXTENSIONS: AnyExtension[] = [
  StarterKit,
  PreparedTableNode,
  WorkPlanNode,
  WebSourceLink,
  PlayableElementHeadingAttributes,
  CalloutNode,
  ...DECISION_CONSEQUENCE_EXTENSIONS,
  ...PLAN_TABLE_EXTENSIONS,
  RunbookReferenceNode,
  GraphNodeReferenceNode,
  MediaImageNode,
];

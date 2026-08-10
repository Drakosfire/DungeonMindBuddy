import type { ReactNode } from "react";

import type { SurfaceInteractionIdentity } from "../types";

export interface SurfaceContextContribution {
  id: string;
  order: number;
  surfaceIdentity: SurfaceInteractionIdentity;
  content: ReactNode;
}

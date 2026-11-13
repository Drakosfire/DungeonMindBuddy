import { deferredComponent } from "../ui/deferredComponent";

export const DeferredMediaImageWizard = deferredComponent(
  () => import("./MediaImageWizard").then(({ MediaImageWizard }) => ({ default: MediaImageWizard })),
  "Image Studio",
);

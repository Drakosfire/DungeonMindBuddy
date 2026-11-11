import { createRoot } from "react-dom/client";
import { NativeGraphDemo } from "./NativeGraphDemo";

const rootElement = document.getElementById("root");
if (!rootElement) throw new Error("The native graph demo root element is missing.");

createRoot(rootElement).render(<NativeGraphDemo />);

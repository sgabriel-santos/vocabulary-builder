import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "./index.css";

const rootElement = document.getElementById("root");
if (!rootElement) throw new Error("Elemento #root não encontrado");

createRoot(rootElement).render(
  <StrictMode>
    <main className="p-4">Vocabulary Builder</main>
  </StrictMode>,
);

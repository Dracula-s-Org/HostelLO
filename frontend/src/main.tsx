import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "./lib/auth";
import { App } from "./App";
import { initPendo } from "./lib/pendo";
import "./index.css";

// Product analytics — auto-captures pages/clicks; custom events fire via pendoTrack().
initPendo();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
);

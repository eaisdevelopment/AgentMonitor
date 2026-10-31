import { createRoot } from "react-dom/client";

import { DashboardApp } from "./app/DashboardApp";
import "./app/dashboard.css";

const root = document.getElementById("agentmonitor-dashboard-root");
if (root === null) throw new Error("dashboard_root_missing");
createRoot(root).render(<DashboardApp />);

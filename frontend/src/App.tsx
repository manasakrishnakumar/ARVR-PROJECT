import { lazy, Suspense, type ReactElement } from "react";
import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import AccountPage from "./pages/AccountPage";
import Landing from "./pages/Landing";
import Library from "./pages/Library";
import NotFound from "./pages/NotFound";
import Settings from "./pages/Settings";

// heavy pages (charts, pose estimation) load on demand so the landing page stays light
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Research = lazy(() => import("./pages/Research"));
const SessionPage = lazy(() => import("./pages/SessionPage"));
const SessionSummary = lazy(() => import("./pages/SessionSummary"));

const wait = (el: ReactElement) => <Suspense fallback={<p className="muted">Loading...</p>}>{el}</Suspense>;

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Landing />} />
        <Route path="exercises" element={<Library />} />
        <Route path="session" element={wait(<SessionPage />)} />
        <Route path="sessions/:id" element={wait(<SessionSummary />)} />
        <Route path="dashboard" element={wait(<Dashboard />)} />
        <Route path="research" element={wait(<Research />)} />
        <Route path="settings" element={<Settings />} />
        <Route path="account" element={<AccountPage />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}

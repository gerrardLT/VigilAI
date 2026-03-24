import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import { ErrorBoundary } from './components/ErrorBoundary'
import WorkspacePage from './pages/WorkspacePage'
import ActivitiesPage from './pages/ActivitiesPage'
import ActivityDetailPage from './pages/ActivityDetailPage'
import TrackingPage from './pages/TrackingPage'
import DigestsPage from './pages/DigestsPage'
import SourcesPage from './pages/SourcesPage'
import DashboardPage from './pages/DashboardPage'
import NotFoundPage from './pages/NotFoundPage'

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<WorkspacePage />} />
            <Route path="workspace" element={<WorkspacePage />} />
            <Route path="activities" element={<ActivitiesPage />} />
            <Route path="activities/:id" element={<ActivityDetailPage />} />
            <Route path="tracking" element={<TrackingPage />} />
            <Route path="digests" element={<DigestsPage />} />
            <Route path="sources" element={<SourcesPage />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  )
}

export default App

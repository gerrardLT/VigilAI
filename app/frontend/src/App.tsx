import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { ErrorBoundary } from './components/ErrorBoundary'
import AgentWorkspacePage from './pages/AgentWorkspacePage'
import SourcesPage from './pages/SourcesPage'
import NotFoundPage from './pages/NotFoundPage'
import SelectionWorkspacePage from './pages/selection/SelectionWorkspacePage'
import SelectionOpportunitiesPage from './pages/selection/SelectionOpportunitiesPage'
import SelectionOpportunityDetailPage from './pages/selection/SelectionOpportunityDetailPage'
import SelectionComparePage from './pages/selection/SelectionComparePage'
import SelectionTrackingPage from './pages/selection/SelectionTrackingPage'
import RewardOverviewPage from './pages/reward/RewardOverviewPage'
import RewardOpportunitiesPage from './pages/reward/RewardOpportunitiesPage'
import RewardOpportunityDetailPage from './pages/reward/RewardOpportunityDetailPage'
import RewardOperationsPage from './pages/reward/RewardOperationsPage'
import RewardSourceDetailPage from './pages/reward/RewardSourceDetailPage'

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to="agent" replace />} />
            <Route path="agent" element={<AgentWorkspacePage />} />
            <Route path="sources" element={<SourcesPage />} />
            <Route path="selection/workspace" element={<SelectionWorkspacePage />} />
            <Route path="selection/opportunities" element={<SelectionOpportunitiesPage />} />
            <Route path="selection/opportunities/:id" element={<SelectionOpportunityDetailPage />} />
            <Route path="selection/compare" element={<SelectionComparePage />} />
            <Route path="selection/tracking" element={<SelectionTrackingPage />} />
            <Route path="rewards">
              <Route index element={<Navigate to="overview" replace />} />
              <Route path="overview" element={<RewardOverviewPage />} />
              <Route path="opportunities" element={<RewardOpportunitiesPage />} />
              <Route path="opportunities/:id" element={<RewardOpportunityDetailPage />} />
              <Route path="operations" element={<RewardOperationsPage />} />
              <Route path="sources/:id" element={<RewardSourceDetailPage />} />
            </Route>
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  )
}

export default App

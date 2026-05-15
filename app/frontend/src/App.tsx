import { BrowserRouter, Navigate, Route, Routes, useLocation, useParams } from 'react-router-dom'
import { ErrorBoundary } from './components/ErrorBoundary'
import DomainShellLayout from './components/app/DomainShellLayout'
import WorkspacePage from './pages/WorkspacePage'
import AgentWorkspacePage from './pages/AgentWorkspacePage'
import ActivitiesPage from './pages/ActivitiesPage'
import ActivityDetailPage from './pages/ActivityDetailPage'
import TrackingPage from './pages/TrackingPage'
import DigestsPage from './pages/DigestsPage'
import SourcesPage from './pages/SourcesPage'
import DashboardPage from './pages/DashboardPage'
import AnalysisTemplatesPage from './pages/AnalysisTemplatesPage'
import AnalysisResultsPage from './pages/AnalysisResultsPage'
import NotFoundPage from './pages/NotFoundPage'
import SelectionWorkspacePage from './pages/selection/SelectionWorkspacePage'
import SelectionOpportunitiesPage from './pages/selection/SelectionOpportunitiesPage'
import SelectionOpportunityDetailPage from './pages/selection/SelectionOpportunityDetailPage'
import SelectionComparePage from './pages/selection/SelectionComparePage'
import SelectionTrackingPage from './pages/selection/SelectionTrackingPage'
import SystemHomePage from './pages/SystemHomePage'
import { agentPaths, opportunityPaths, selectionPaths } from './routes/domainPaths'

const opportunityNavLinks = [
  { path: opportunityPaths.workspace, label: '工作台' },
  { path: opportunityPaths.activities, label: '机会池' },
  { path: opportunityPaths.analysisResults, label: '分析结果' },
  { path: opportunityPaths.analysisTemplates, label: '分析模板' },
  { path: opportunityPaths.tracking, label: '跟进' },
  { path: opportunityPaths.digests, label: '日报' },
  { path: opportunityPaths.sources, label: '来源' },
]

const agentNavLinks = [{ path: agentPaths.home, label: '会话工作台' }]

const selectionNavLinks = [
  { path: selectionPaths.workspace, label: '工作台' },
  { path: selectionPaths.opportunities, label: '机会池' },
  { path: selectionPaths.compare, label: '对比' },
  { path: selectionPaths.tracking, label: '跟进' },
]

function LegacyActivityDetailRedirect() {
  const { id } = useParams<{ id: string }>()
  const location = useLocation()
  return <Navigate to={`${opportunityPaths.activityDetail(id ?? '')}${location.search}`} replace />
}

function LegacyPathRedirect({ to }: { to: string }) {
  const location = useLocation()
  return <Navigate to={`${to}${location.search}`} replace />
}

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<SystemHomePage />} />

          <Route
            path="/opportunity"
            element={
              <DomainShellLayout
                brandLabel="旧机会系统"
                brandTo={opportunityPaths.workspace}
                navLinks={opportunityNavLinks}
              />
            }
          >
            <Route index element={<Navigate to="workspace" replace />} />
            <Route path="workspace" element={<WorkspacePage />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="activities" element={<ActivitiesPage />} />
            <Route path="activities/:id" element={<ActivityDetailPage />} />
            <Route path="analysis/results" element={<AnalysisResultsPage />} />
            <Route path="analysis/templates" element={<AnalysisTemplatesPage />} />
            <Route path="tracking" element={<TrackingPage />} />
            <Route path="digests" element={<DigestsPage />} />
            <Route path="sources" element={<SourcesPage />} />
          </Route>

          <Route
            path="/agent"
            element={
              <DomainShellLayout
                brandLabel="Agent 平台"
                brandTo={agentPaths.home}
                navLinks={agentNavLinks}
              />
            }
          >
            <Route index element={<AgentWorkspacePage />} />
          </Route>

          <Route
            path="/selection"
            element={
              <DomainShellLayout
                brandLabel="选品域"
                brandTo={selectionPaths.workspace}
                navLinks={selectionNavLinks}
              />
            }
          >
            <Route index element={<Navigate to="workspace" replace />} />
            <Route path="workspace" element={<SelectionWorkspacePage />} />
            <Route path="opportunities" element={<SelectionOpportunitiesPage />} />
            <Route path="opportunities/:id" element={<SelectionOpportunityDetailPage />} />
            <Route path="compare" element={<SelectionComparePage />} />
            <Route path="tracking" element={<SelectionTrackingPage />} />
          </Route>

          <Route path="/workspace" element={<LegacyPathRedirect to={opportunityPaths.workspace} />} />
          <Route path="/dashboard" element={<LegacyPathRedirect to={opportunityPaths.dashboard} />} />
          <Route path="/activities" element={<LegacyPathRedirect to={opportunityPaths.activities} />} />
          <Route path="/activities/:id" element={<LegacyActivityDetailRedirect />} />
          <Route path="/analysis/results" element={<LegacyPathRedirect to={opportunityPaths.analysisResults} />} />
          <Route path="/analysis/templates" element={<LegacyPathRedirect to={opportunityPaths.analysisTemplates} />} />
          <Route path="/tracking" element={<LegacyPathRedirect to={opportunityPaths.tracking} />} />
          <Route path="/digests" element={<LegacyPathRedirect to={opportunityPaths.digests} />} />
          <Route path="/sources" element={<LegacyPathRedirect to={opportunityPaths.sources} />} />

          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  )
}

export default App

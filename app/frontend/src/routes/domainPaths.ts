export const systemPaths = {
  home: '/',
} as const

export const agentPaths = {
  home: '/agent',
} as const

export const opportunityPaths = {
  root: '/opportunity',
  workspace: '/opportunity/workspace',
  dashboard: '/opportunity/dashboard',
  activities: '/opportunity/activities',
  activityDetail: (id: string) => `/opportunity/activities/${id}`,
  tracking: '/opportunity/tracking',
  digests: '/opportunity/digests',
  sources: '/opportunity/sources',
  analysisResults: '/opportunity/analysis/results',
  analysisTemplates: '/opportunity/analysis/templates',
} as const

export const selectionPaths = {
  root: '/selection',
  workspace: '/selection/workspace',
  opportunities: '/selection/opportunities',
  opportunityDetail: (id: string) => `/selection/opportunities/${id}`,
  compare: '/selection/compare',
  tracking: '/selection/tracking',
} as const

export const rewardPaths = {
  root: '/rewards',
  overview: '/rewards/overview',
  opportunities: '/rewards/opportunities',
  opportunityDetail: (id: string) => `/rewards/opportunities/${id}`,
  operations: '/rewards/operations',
  sourceDetail: (id: string) => `/rewards/sources/${id}`,
  workspace: '/rewards/workspace',
} as const

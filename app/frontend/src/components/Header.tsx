import { DomainHeader } from './app/DomainHeader'
import { agentPaths, opportunityPaths, selectionPaths, systemPaths } from '../routes/domainPaths'

const navLinks = [
  { path: systemPaths.home, label: '系统入口' },
  { path: opportunityPaths.workspace, label: '旧机会系统' },
  { path: agentPaths.home, label: 'Agent 平台' },
  { path: selectionPaths.workspace, label: '选品域' },
]

export function Header() {
  return <DomainHeader brandLabel="VigilAI" brandTo={systemPaths.home} navLinks={navLinks} />
}

export default Header

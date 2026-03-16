import { APP_NAME, APP_VERSION, APP_DESCRIPTION } from '../utils/constants'

/**
 * 页脚组件
 */
export function Footer() {
  return (
    <footer className="bg-gray-50 border-t border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-2 text-sm text-gray-500">
          <div className="flex items-center gap-2">
            <span className="text-lg">🎯</span>
            <span>{APP_NAME} - {APP_DESCRIPTION}</span>
          </div>
          <div>
            版本 {APP_VERSION}
          </div>
        </div>
      </div>
    </footer>
  )
}

export default Footer

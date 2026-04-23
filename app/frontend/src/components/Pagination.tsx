interface PaginationProps {
  page: number
  totalPages: number
  onPageChange: (page: number) => void
}

/**
 * 分页组件
 */
export function Pagination({ page, totalPages, onPageChange }: PaginationProps) {
  if (totalPages <= 1) {
    return null
  }

  // 生成页码数组
  const getPageNumbers = () => {
    const pages: Array<number | '...'> = []
    const showPages = 5 // 显示的页码数量

    if (totalPages <= showPages) {
      // 总页数小于等于显示数量，显示所有页码
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i)
      }
    } else {
      // 总页数大于显示数量，显示部分页码
      if (page <= 3) {
        // 当前页靠近开头
        for (let i = 1; i <= 4; i++) {
          pages.push(i)
        }
        pages.push('...')
        pages.push(totalPages)
      } else if (page >= totalPages - 2) {
        // 当前页靠近结尾
        pages.push(1)
        pages.push('...')
        for (let i = totalPages - 3; i <= totalPages; i++) {
          pages.push(i)
        }
      } else {
        // 当前页在中间
        pages.push(1)
        pages.push('...')
        for (let i = page - 1; i <= page + 1; i++) {
          pages.push(i)
        }
        pages.push('...')
        pages.push(totalPages)
      }
    }

    return pages
  }

  return (
    <nav aria-label="分页导航" className="flex items-center justify-center gap-1">
      {/* 上一页 */}
      <button
        type="button"
        aria-label="上一页"
        onClick={() => onPageChange(page - 1)}
        disabled={page === 1}
        className="min-h-[44px] rounded-lg px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50 hover:bg-gray-100"
      >
        上一页
      </button>

      {/* 页码 */}
      {getPageNumbers().map((pageNum, index) => (
        pageNum === '...' ? (
          <span key={`ellipsis-${index}`} aria-hidden="true" className="px-2 text-sm text-gray-500">
            ...
          </span>
        ) : (
          <button
            key={pageNum}
            type="button"
            aria-label={`第 ${pageNum} 页`}
            aria-current={pageNum === page ? 'page' : undefined}
            onClick={() => onPageChange(pageNum)}
            className={`h-11 w-11 rounded-lg text-sm font-medium ${
              pageNum === page ? 'bg-primary-600 text-white' : 'hover:bg-gray-100'
            }`}
          >
            {pageNum}
          </button>
        )
      ))}

      {/* 下一页 */}
      <button
        type="button"
        aria-label="下一页"
        onClick={() => onPageChange(page + 1)}
        disabled={page === totalPages}
        className="min-h-[44px] rounded-lg px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50 hover:bg-gray-100"
      >
        下一页
      </button>
    </nav>
  )
}

export default Pagination

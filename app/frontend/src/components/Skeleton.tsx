interface SkeletonProps {
  width?: string | number
  height?: string | number
  className?: string
  variant?: 'text' | 'circular' | 'rectangular'
}

const variantClasses: Record<NonNullable<SkeletonProps['variant']>, string> = {
  text: 'rounded-md h-4',
  circular: 'rounded-full',
  rectangular: 'rounded-lg',
}

/**
 * 骨架屏加载组件
 * 支持 text、circular、rectangular 三种变体
 */
export function Skeleton({
  width,
  height,
  className = '',
  variant = 'text',
}: SkeletonProps) {
  const style: React.CSSProperties = {}
  if (width) style.width = typeof width === 'number' ? `${width}px` : width
  if (height) style.height = typeof height === 'number' ? `${height}px` : height

  return (
    <div
      role="status"
      aria-label="加载中"
      aria-busy="true"
      style={style}
      className={`animate-pulse bg-slate-200 ${variantClasses[variant]} ${className}`}
    >
      <span className="sr-only">加载中...</span>
    </div>
  )
}

export default Skeleton

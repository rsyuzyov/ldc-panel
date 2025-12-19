import { useLoading } from '../contexts/LoadingContext'

export function LoadingOverlay() {
  const { isLoading, loadingMessage } = useLoading()

  if (!isLoading) return null

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50">
      <div className="relative w-12 h-12">
        <div className="absolute inset-0 border-4 border-gray-300 rounded-full"></div>
        <div className="absolute inset-0 border-4 border-gray-500 rounded-full border-t-transparent animate-spin"></div>
      </div>
    </div>
  )
}

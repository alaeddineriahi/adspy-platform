/** Pulse placeholder matching AdCard's proportions — shown while results load. */
export function SkeletonCard() {
  return (
    <div className="bg-white rounded-2xl border border-[#e6e6e7] overflow-hidden animate-pulse">
      <div className="aspect-video bg-gray-100" />
      <div className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="h-3.5 bg-gray-100 rounded-full w-1/3" />
          <div className="h-3.5 bg-gray-100 rounded-full w-12" />
        </div>
        <div className="h-3 bg-gray-100 rounded-full w-full" />
        <div className="h-3 bg-gray-100 rounded-full w-2/3" />
        <div className="flex gap-2 pt-1">
          <div className="h-8 bg-gray-100 rounded-full flex-1" />
          <div className="h-8 w-8 bg-gray-100 rounded-full" />
        </div>
      </div>
    </div>
  );
}

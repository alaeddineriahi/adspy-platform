import { Bookmark } from "lucide-react";

export default function SavedPage() {
  return (
    <div className="p-8 max-w-5xl">
      <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-2">
        <Bookmark className="w-6 h-6" /> Saved ads
      </h2>
      <div className="text-center py-20 text-gray-400">
        <Bookmark className="w-12 h-12 mx-auto mb-4 opacity-50" />
        <p className="text-lg">No saved ads yet</p>
        <p className="text-sm mt-2">Save ads from search to build your swipe file.</p>
      </div>
    </div>
  );
}

import { Settings } from "lucide-react";

export default function SettingsPage() {
  return (
    <div className="p-8 max-w-3xl">
      <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-2">
        <Settings className="w-6 h-6" /> Settings
      </h2>
      <div className="bg-white border border-gray-200 rounded-xl p-6">
        <h3 className="font-semibold text-gray-900 mb-2">Plan</h3>
        <p className="text-sm text-gray-600">
          You are on the <span className="font-medium">Free</span> plan. Billing
          is not configured yet.
        </p>
      </div>
    </div>
  );
}

import { redirect } from "next/navigation";

/** Ingestion now lives under the admin backoffice (it's an admin-only, expensive action). */
export default function IngestionRedirect() {
  redirect("/admin/ingestion");
}

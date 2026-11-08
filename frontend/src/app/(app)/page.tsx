import { redirect } from "next/navigation";

import { AlertIcon } from "@/components/icons";
import { requireCurrentUser } from "@/lib/current-user";
import { getEnabledModules } from "@/lib/module-settings";
import { firstEnabledModuleHref } from "@/lib/modules";

export default async function HomePage() {
  const user = await requireCurrentUser();
  const destination = firstEnabledModuleHref(
    getEnabledModules(),
    user.role === "admin",
  );
  if (destination) {
    redirect(destination);
  }

  return (
    <div className="mx-auto max-w-lg rounded-2xl border border-amber-200 bg-amber-50 px-6 py-12 text-center">
      <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-amber-100 text-amber-700">
        <AlertIcon className="size-6" />
      </span>
      <h1 className="mt-4 text-lg font-semibold text-slate-900">Aucun module actif</h1>
      <p className="mt-2 text-sm text-slate-600">
        Active au moins un module dans le fichier <code>.env</code>, puis recrée le service
        frontend avec <code>docker compose up -d</code>.
      </p>
    </div>
  );
}

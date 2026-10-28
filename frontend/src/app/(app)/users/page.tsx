import { UsersIcon } from "@/components/icons";
import { CreateUserDialog } from "@/components/users/create-user-dialog";
import { EditUserDialog } from "@/components/users/edit-user-dialog";
import { ResetPasswordButton } from "@/components/users/reset-password-button";
import { apiFetch } from "@/lib/api";
import { formatDateTimeUtc } from "@/lib/format";
import type { CurrentUser, UserAccount } from "@/lib/types";
import {
  USER_ROLE_BADGES,
  USER_ROLE_LABELS,
  USER_STATUS_BADGES,
} from "@/lib/users";

function AccessDenied() {
  return (
    <div className="rounded-2xl border border-amber-200 bg-amber-50 px-6 py-12 text-center">
      <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-amber-100 text-amber-700">
        <UsersIcon className="size-6" />
      </span>
      <h1 className="mt-4 text-base font-semibold text-slate-900">
        Gestion des utilisateurs réservée aux administrateurs
      </h1>
      <p className="mx-auto mt-1 max-w-sm text-sm text-slate-600">
        Demande à un administrateur de créer ou de modifier les comptes.
      </p>
    </div>
  );
}

export default async function UsersPage() {
  const currentUser = await apiFetch<CurrentUser>("/api/v1/auth/me");
  if (currentUser.role !== "admin") {
    return <AccessDenied />;
  }

  const users = await apiFetch<UserAccount[]>("/api/v1/users");

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-teal-700">Administration</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 lg:text-3xl">
            Utilisateurs
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-500">
            Gère les comptes et leurs droits. Les mots de passe sont générés par le serveur et ne
            sont affichés qu’une seule fois.
          </p>
        </div>
        <CreateUserDialog />
      </header>

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <header className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Comptes</h2>
            <p className="mt-0.5 text-xs text-slate-500">
              {users.length} compte{users.length === 1 ? "" : "s"}
            </p>
          </div>
          <UsersIcon className="size-5 text-slate-400" />
        </header>

        {users.length === 0 ? (
          <p className="px-5 py-10 text-center text-sm text-slate-500">
            Aucun compte n’est disponible.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-3 font-semibold">Email</th>
                  <th className="px-5 py-3 font-semibold">Rôle</th>
                  <th className="px-5 py-3 font-semibold">Statut</th>
                  <th className="px-5 py-3 font-semibold">Créé le</th>
                  <th className="px-5 py-3 font-semibold">Modifié le</th>
                  <th className="px-5 py-3 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {users.map((user) => {
                  const isSelf = user.id === currentUser.id;
                  return (
                    <tr key={`${user.id}:${user.updated_at}`} className="align-middle">
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-slate-900">{user.email}</span>
                          {isSelf ? (
                            <span className="rounded-full bg-teal-50 px-2 py-0.5 text-[11px] font-semibold text-teal-700">
                              Vous
                            </span>
                          ) : null}
                        </div>
                      </td>
                      <td className="px-5 py-3">
                        <span
                          className={`rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${USER_ROLE_BADGES[user.role]}`}
                        >
                          {USER_ROLE_LABELS[user.role]}
                        </span>
                      </td>
                      <td className="px-5 py-3">
                        <span
                          className={`rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${
                            user.is_active ? USER_STATUS_BADGES.active : USER_STATUS_BADGES.inactive
                          }`}
                        >
                          {user.is_active ? "Actif" : "Inactif"}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-5 py-3 text-slate-600">
                        {formatDateTimeUtc(user.created_at)}
                      </td>
                      <td className="whitespace-nowrap px-5 py-3 text-slate-600">
                        {formatDateTimeUtc(user.updated_at)}
                      </td>
                      <td className="px-5 py-3">
                        <div className="flex items-start justify-end gap-1">
                          <EditUserDialog user={user} isSelf={isSelf} />
                          <ResetPasswordButton user={user} isSelf={isSelf} />
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

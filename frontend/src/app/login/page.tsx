import { SnowflakeIcon } from "@/components/icons";
import { LoginForm } from "@/components/login-form";

export default function LoginPage() {
  return (
    <main className="grid min-h-screen lg:grid-cols-2">
      <section className="relative hidden flex-col justify-between overflow-hidden bg-slate-900 p-12 text-slate-100 lg:flex">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-24 -top-24 size-96 rounded-full bg-teal-500/20 blur-3xl"
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -bottom-32 -left-20 size-96 rounded-full bg-sky-500/10 blur-3xl"
        />

        <div className="relative flex items-center gap-3">
          <span className="grid size-11 place-items-center rounded-xl bg-teal-500/15 text-teal-300 ring-1 ring-teal-400/30">
            <SnowflakeIcon className="size-6" />
          </span>
          <span className="text-lg font-semibold tracking-tight">haccpFlow</span>
        </div>

        <div className="relative max-w-md space-y-4">
          <h1 className="text-3xl font-semibold leading-tight tracking-tight">
            La chaîne du froid, sous contrôle.
          </h1>
          <p className="text-slate-400">
            Suivez vos enceintes réfrigérées, leurs seuils réglementaires et les relevés de
            température — automatiques ou manuels — depuis un seul endroit.
          </p>
        </div>

        <p className="relative text-xs text-slate-500">
          Traçabilité HACCP · Relevés horodatés en UTC
        </p>
      </section>

      <section className="flex items-center justify-center px-6 py-16">
        <div className="w-full max-w-sm animate-fade-in">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <span className="grid size-10 place-items-center rounded-xl bg-teal-600/10 text-teal-700">
              <SnowflakeIcon className="size-5" />
            </span>
            <span className="text-base font-semibold tracking-tight">haccpFlow</span>
          </div>

          <h2 className="text-2xl font-semibold tracking-tight text-slate-900">Connexion</h2>
          <p className="mt-1 text-sm text-slate-500">
            Accède à la gestion de ton parc d&apos;équipements.
          </p>

          <div className="mt-8">
            <LoginForm />
          </div>
        </div>
      </section>
    </main>
  );
}

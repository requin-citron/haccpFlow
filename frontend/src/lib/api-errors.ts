import { t, type Locale, type MessageKey } from "@/lib/i18n";

type ApiErrorLike = {
  status: number;
  code: string;
  message: string;
};

type TranslateApiErrorOptions = {
  notFound?: MessageKey;
  conflict?: MessageKey;
  invalid?: MessageKey;
};

function isApiErrorLike(error: unknown): error is ApiErrorLike {
  if (typeof error !== "object" || error === null) {
    return false;
  }
  const candidate = error as Partial<ApiErrorLike>;
  return (
    typeof candidate.status === "number" &&
    typeof candidate.code === "string" &&
    typeof candidate.message === "string"
  );
}

const ERROR_CODE_KEYS: Record<string, MessageKey> = {
  invalid_token: "Ta session a expiré, reconnecte-toi.",
  insufficient_role: "Cette action est réservée aux administrateurs.",
  equipment_not_found: "Ce matériel n'existe plus.",
  equipment_name_conflict: "Un matériel actif porte déjà ce nom.",
  invalid_threshold_configuration:
    "Vérifie les seuils : les deux doivent être renseignés ensemble, et le minimum doit rester inférieur au maximum.",
  cleaning_plan_not_found: "Ce plan de nettoyage n'existe plus.",
  cleaning_plan_name_conflict: "Un plan actif porte déjà ce nom.",
  cleaning_record_not_found: "Déclaration introuvable.",
  pasteurisation_not_found: "Ce lot de pasteurisation n'existe plus.",
  transport_not_found: "Ce transport n'existe plus.",
  vehicle_conflict: "Un véhicule actif utilise déjà ce nom ou cette plaque.",
  cash_register_not_found: "Cette caisse n'existe plus.",
  cash_register_name_conflict: "Une caisse active porte déjà ce nom.",
  cash_session_not_found: "Ce suivi de caisse n'existe plus.",
  cash_expense_not_found: "Frais introuvable.",
  user_not_found: "Ce compte n'existe plus.",
  cash_session_already_open:
    "Cette caisse a déjà un suivi ouvert : clôture-le avant d'en ouvrir un nouveau.",
  cash_session_closed: "Ce suivi est clôturé : il ne peut plus être modifié.",
  cash_session_date_in_future:
    "Impossible d'enregistrer un suivi à plus d'un jour dans le futur.",
  cash_register_has_open_session:
    "Cette caisse a un suivi ouvert : clôture-le d'abord.",
  cleaning_date_out_of_range:
    "Impossible de déclarer un nettoyage à plus d'un jour dans le futur.",
  reading_date_out_of_range:
    "Impossible de saisir un relevé à plus d'un jour dans le futur.",
  pasteurisation_date_out_of_range:
    "Impossible d'enregistrer un lot à plus d'un jour dans le futur.",
  pasteurisation_end_before_start:
    "L'heure de fin doit être postérieure à l'heure de début.",
  pasteurisation_phase_time_invalid:
    "L'heure de fin doit être postérieure à l'heure de début.",
  transport_date_out_of_range:
    "Impossible d'enregistrer un transport à plus d'un jour dans le futur.",
  vehicle_not_found: "Ce véhicule n'existe plus.",
  user_email_taken: "Un compte utilise déjà cet email.",
  user_last_admin:
    "Le dernier administrateur actif ne peut pas être désactivé ou supprimé.",
  user_self_lockout:
    "Tu ne peux pas modifier tes propres droits, désactiver ou supprimer ton compte.",
  reading_value_required: "Saisis au moins une température.",
  export_range_invalid: "La date de début doit précéder la date de fin.",
  template_name_taken: "Un modèle porte déjà ce nom. Choisis-en un autre.",
  template_too_large: "Le fichier dépasse la taille maximale autorisée.",
  template_type_not_allowed: "Seuls les fichiers .tex sont acceptés.",
  template_empty: "Le fichier est vide.",
  template_invalid_encoding:
    "Le fichier doit être un texte LaTeX UTF-8 valide, sans caractères binaires.",
  template_invalid_content:
    "Le fichier doit être un texte LaTeX UTF-8 valide, sans caractères binaires.",
  template_name_invalid: "Le nom du modèle est invalide.",
  template_file_required: "Choisis un fichier à importer.",
  template_invalid_multipart: "La requête d'import est invalide.",
  template_not_found: "Ce modèle n'existe plus.",
  template_file_missing: "Le fichier source du modèle est introuvable.",
  template_variable_name_taken: "Ce nom de variable est déjà utilisé sur ce modèle.",
  template_variable_invalid: "La variable est invalide.",
  template_variable_not_found: "Cette variable n'existe plus.",
  template_value_invalid: "La valeur est invalide.",
  template_image_type_not_allowed: "Formats acceptés : JPEG ou PNG.",
  template_image_too_large: "L'image dépasse la taille maximale autorisée (5 Mio).",
  template_image_not_found: "Aucune image n'est associée à cette variable.",
  template_values_missing: "Des valeurs obligatoires sont manquantes.",
  template_values_unknown: "Une valeur ne correspond à aucune variable du modèle.",
  template_values_static: "Une variable statique a été fournie par erreur.",
  template_syntax_error: "Le modèle contient une syntaxe invalide.",
  template_render_failed: "Le modèle n'a pas pu être rendu avec ces valeurs.",
  template_render_too_large: "Le document généré est trop volumineux.",
  template_compilation_failed: "La compilation LaTeX du document a échoué.",
  template_compilation_timeout: "La compilation LaTeX a dépassé le délai autorisé.",
  template_image_missing:
    "Une image attendue par le modèle est absente. Un administrateur doit la téléverser.",
  pdf_compiler_unavailable: "Le compilateur PDF est indisponible.",
};

export function translateApiError(
  error: unknown,
  locale: Locale,
  options: TranslateApiErrorOptions = {},
): string {
  if (!isApiErrorLike(error)) {
    return t(locale, "Une erreur inattendue est survenue.");
  }

  const codeKey = ERROR_CODE_KEYS[error.code];
  if (codeKey) {
    return t(locale, codeKey);
  }

  switch (error.status) {
    case 401:
      return t(locale, "Ta session a expiré, reconnecte-toi.");
    case 403:
      return t(locale, "Cette action est réservée aux administrateurs.");
    case 404:
      return t(locale, options.notFound ?? "Cette action n'est plus disponible.");
    case 409:
      return t(locale, options.conflict ?? "Le changement a échoué.");
    case 422:
      return t(locale, options.invalid ?? "Vérifie les valeurs saisies, puis réessaie.");
    default:
      return error.code.startsWith("http_")
        ? t(locale, "Le serveur a renvoyé une erreur inattendue.")
        : error.message;
  }
}

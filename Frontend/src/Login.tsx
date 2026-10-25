import { useState } from "react";
import { signInWithEmailAndPassword } from "firebase/auth";
import { auth } from "./firebase";
import {
  Mail,
  Lock,
  Eye,
  EyeOff,
  Sparkles,
  ArrowRight,
  ShieldCheck,
} from "lucide-react";

function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!email || !password) {
      setError("Veuillez remplir tous les champs.");
      return;
    }

    setError("");
    setLoading(true);

    try {
      await signInWithEmailAndPassword(auth, email, password);
    } catch (error: any) {
      console.error("Login error:", error);

      switch (error.code) {
        case "auth/invalid-credential":
          setError("Email ou mot de passe incorrect.");
          break;

        case "auth/user-not-found":
          setError("Aucun compte associé à cet email.");
          break;

        case "auth/wrong-password":
          setError("Mot de passe incorrect.");
          break;

        case "auth/invalid-email":
          setError("Adresse email invalide.");
          break;

        case "auth/too-many-requests":
          setError(
            "Trop de tentatives. Veuillez patienter quelques instants."
          );
          break;

        default:
          setError("Une erreur est survenue. Veuillez réessayer.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f8f7fb] flex items-center justify-center px-6 py-10">

      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-32 -left-32 h-96 w-96 rounded-full bg-violet-200/30 blur-3xl" />
        <div className="absolute -bottom-32 -right-32 h-96 w-96 rounded-full bg-indigo-200/30 blur-3xl" />
      </div>

      <div className="relative w-full max-w-md">

        {/* Logo */}
        <div className="mb-8 text-center">
          <img
            src="/MEFai.png"
            alt="Logo du Ministère"
            className="mx-auto mb-5 h-24 w-24 object-contain"
          />

          {/*<h1 className="text-3xl font-bold tracking-tight text-slate-900">
            MEFai
          </h1>*/}

          <p className="mt-2 text-sm text-slate-500">
            Assistant intelligent du Ministère
          </p>

        </div>

        {/* Login Card */}
        <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-xl shadow-slate-200/50">

          <div className="mb-7">
            <h2 className="text-xl font-bold text-slate-900">
              Connexion
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Connectez-vous pour accéder à votre assistant.
            </p>
          </div>

          <form onSubmit={handleLogin} className="space-y-5">

            {/* Email */}
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">
                Adresse e-mail
              </label>

              <div className="relative">

                <Mail
                  size={18}
                  className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
                />

                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="vous@ministere.ma"
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 py-3.5 pl-11 pr-4 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-violet-400 focus:bg-white focus:ring-4 focus:ring-violet-100"
                />

              </div>
            </div>

            {/* Password */}
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">
                Mot de passe
              </label>

              <div className="relative">

                <Lock
                  size={18}
                  className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400"
                />

                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="••••••••"
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 py-3.5 pl-11 pr-12 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-violet-400 focus:bg-white focus:ring-4 focus:ring-violet-100"
                />

                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
                >
                  {showPassword ? (
                    <EyeOff size={18} />
                  ) : (
                    <Eye size={18} />
                  )}
                </button>

              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
                {error}
              </div>
            )}

            {/* Login button */}
            <button
              type="submit"
              disabled={loading}
              className="group flex w-full items-center justify-center gap-2 rounded-xl bg-violet-600 px-4 py-3.5 text-sm font-semibold text-white shadow-lg shadow-violet-200 transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  Connexion...
                </>
              ) : (
                <>
                  Se connecter
                  <ArrowRight
                    size={17}
                    className="transition-transform group-hover:translate-x-1"
                  />
                </>
              )}
            </button>

          </form>

          {/* Security */}
          <div className="mt-7 flex items-center justify-center gap-2 border-t border-slate-100 pt-6 text-xs text-slate-400">
            <ShieldCheck size={15} className="text-violet-500" />
            <span>Connexion sécurisée par Firebase</span>
          </div>

        </div>

        {/* Footer */}
        <p className="mt-6 text-center text-xs text-slate-400">
          Accès réservé aux utilisateurs autorisés
        </p>

      </div>
    </div>
  );
}

export default Login;
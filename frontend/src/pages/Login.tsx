import { Navigate, useLocation, useSearchParams } from "react-router-dom";
import { ShieldCheck, HardDrive, CheckCircle2, ArrowRight } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { authApi } from "../api/auth";

export function Login() {
  const { isAuthenticated, isLoading, error } = useAuth();
  const location = useLocation();
  const [searchParams] = useSearchParams();

  if (isLoading) {
    return (
      <div className="login-page">
        <div className="login-card loading">
          <p>Checking session...</p>
        </div>
      </div>
    );
  }

  if (isAuthenticated) {
    const from = (location.state as any)?.from?.pathname || "/";
    return <Navigate to={from} replace />;
  }

  const oauthError = searchParams.get("error");
  const errorMessage =
    oauthError === "access_denied"
      ? "Google sign-in was cancelled. Please try again when you are ready."
      : oauthError
        ? "Google sign-in could not be completed. Please try again."
        : error
          ? "We could not verify your session. Please try signing in again."
          : null;

  const handleGoogleLogin = () => {
    window.location.href = authApi.getGoogleLoginUrl();
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-header">
          <div className="login-logo-badge">
            <ShieldCheck size={32} />
          </div>
          <h1>Sign in to Meridian</h1>
          <p className="login-tagline">
            One control library across ISO 27001, SOC 2, and NIST CSF.
          </p>
        </div>

        <div className="login-features">
          <div className="feature-item">
            <CheckCircle2 size={16} className="feature-icon" />
            <span>Single unified control library mapped to 3 frameworks</span>
          </div>
          <div className="feature-item">
            <CheckCircle2 size={16} className="feature-icon" />
            <span>Automated crosswalk, gap analysis, and before/after risk scoring</span>
          </div>
          <div className="feature-item">
            <HardDrive size={16} className="feature-icon" />
            <span>Live evidence verification directly from your Google Drive</span>
          </div>
        </div>

        <div className="login-actions">
          {errorMessage && (
            <p className="login-error" role="alert">
              {errorMessage}
            </p>
          )}
          <button
            type="button"
            className="google-signin-btn"
            onClick={handleGoogleLogin}
          >
            <svg className="google-icon" viewBox="0 0 24 24" width="20" height="20">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
              />
            </svg>
            <span>Sign in with Google</span>
            <ArrowRight size={16} className="btn-arrow" />
          </button>
        </div>

        <div className="login-permissions-info">
          <p className="permissions-title">Permissions requested:</p>
          <p className="permissions-body">
            Identity verification (name, email) and Google Drive file access for
            evidence workbooks you explicitly select. We never alter files outside
            Meridian.
          </p>
        </div>
      </div>
    </div>
  );
}

import { Link } from "react-router-dom";
import { AlertCircle, Home } from "lucide-react";

export function NotFound() {
  return (
    <div className="not-found-page">
      <div className="not-found-card">
        <AlertCircle size={48} className="not-found-icon" />
        <h2>Page Not Found</h2>
        <p>The page you requested does not exist or has moved.</p>
        <Link to="/" className="primary-btn">
          <Home size={16} />
          <span>Back to Dashboard</span>
        </Link>
      </div>
    </div>
  );
}

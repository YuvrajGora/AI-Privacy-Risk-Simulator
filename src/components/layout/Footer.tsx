import React from 'react';
import { Link } from 'react-router-dom';

export const Footer: React.FC = () => {
  return (
    <footer className="mt-auto py-md bg-surface-container-lowest border-t border-outline-variant/10 text-xs text-outline">
      <div className="max-w-[1200px] mx-auto px-6 flex flex-col sm:flex-row justify-between items-center gap-sm">
        <div className="flex items-center gap-2">
          <span className="font-bold text-on-surface">AI PRIVACY RISK SIMULATOR</span>
          <span>•</span>
          <span>Engineered for Forest Precision Analytics</span>
        </div>
        <div className="flex gap-md text-on-surface-variant">
          <Link to="/" className="hover:text-primary transition-colors">Overview</Link>
          <Link to="/results" className="hover:text-primary transition-colors">Documentation</Link>
          <Link to="/settings" className="hover:text-primary transition-colors">System Status</Link>
        </div>
      </div>
    </footer>
  );
};

export default Footer;

import React from 'react';
import { Link } from 'react-router-dom';
import { Compass, ArrowLeft } from 'lucide-react';

export const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 px-4">
      <div className="max-w-md w-full text-center space-y-6 bg-slate-900/60 border border-slate-800 p-8 rounded-2xl backdrop-blur">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-400">
          <Compass className="w-8 h-8" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">404 - Page Not Found</h1>
          <p className="text-sm text-slate-400 mt-2">
            The spatial coordinates or page resource you requested does not exist on this node.
          </p>
        </div>
        <Link
          to="/dashboard"
          className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-100 text-sm font-semibold transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Return to Dashboard</span>
        </Link>
      </div>
    </div>
  );
};

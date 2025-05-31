import React from 'react';
import { User, Shield, FileText, Upload } from 'lucide-react';
import useAuthStore from '../../stores/authStore';
import ModeSwitcher from '../common/ModeSwitcher';

const Dashboard = () => {
  const { user } = useAuthStore();

  const isAuditorMode = user?.user_mode === 'auditor';

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <h1 className="text-2xl font-bold text-gray-900">
              Smart Contract Auditor
            </h1>
            <div className="flex items-center gap-4">
              <ModeSwitcher />
              <div className="flex items-center gap-2">
                {isAuditorMode ? (
                  <Shield className="w-5 h-5 text-purple-600" />
                ) : (
                  <User className="w-5 h-5 text-blue-600" />
                )}
                <span className="text-sm font-medium">
                  {user?.full_name || user?.email}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Mode Info Banner */}
        <div className={`p-4 rounded-lg mb-6 ${
          isAuditorMode 
            ? 'bg-purple-50 border border-purple-200' 
            : 'bg-blue-50 border border-blue-200'
        }`}>
          <div className="flex items-center gap-2">
            {isAuditorMode ? (
              <>
                <Shield className="w-5 h-5 text-purple-600" />
                <h2 className="text-lg font-semibold text-purple-800">
                  Auditor Mode
                </h2>
              </>
            ) : (
              <>
                <User className="w-5 h-5 text-blue-600" />
                <h2 className="text-lg font-semibold text-blue-800">
                  Normal Mode
                </h2>
              </>
            )}
          </div>
          <p className="text-sm mt-1 text-gray-600">
            {isAuditorMode 
              ? 'Advanced analysis tools and options available'
              : 'Basic upload and report viewing functionality'
            }
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Upload Feature - Available in both modes */}
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="flex items-center gap-2 mb-3">
              <Upload className="w-5 h-5 text-green-600" />
              <h3 className="font-semibold">Upload Contract</h3>
            </div>
            <p className="text-sm text-gray-600 mb-4">
              Upload your smart contract for analysis
            </p>
            <button className="w-full bg-green-600 text-white py-2 rounded-md hover:bg-green-700 transition-colors">
              Upload File
            </button>
          </div>

          {/* Reports Feature - Available in both modes */}
          <div className="bg-white p-6 rounded-lg shadow-sm border">
            <div className="flex items-center gap-2 mb-3">
              <FileText className="w-5 h-5 text-blue-600" />
              <h3 className="font-semibold">View Reports</h3>
            </div>
            <p className="text-sm text-gray-600 mb-4">
              Access your generated analysis reports
            </p>
            <button className="w-full bg-blue-600 text-white py-2 rounded-md hover:bg-blue-700 transition-colors">
              View Reports
            </button>
          </div>

          {/* Auditor-only Features */}
          {isAuditorMode && (
            <>
              <div className="bg-white p-6 rounded-lg shadow-sm border">
                <div className="flex items-center gap-2 mb-3">
                  <Shield className="w-5 h-5 text-purple-600" />
                  <h3 className="font-semibold">Advanced Analysis</h3>
                </div>
                <p className="text-sm text-gray-600 mb-4">
                  Configure advanced static analysis options
                </p>
                <button className="w-full bg-purple-600 text-white py-2 rounded-md hover:bg-purple-700 transition-colors">
                  Configure Analysis
                </button>
              </div>

              <div className="bg-white p-6 rounded-lg shadow-sm border">
                <div className="flex items-center gap-2 mb-3">
                  <Settings className="w-5 h-5 text-orange-600" />
                  <h3 className="font-semibold">Prompt Options</h3>
                </div>
                <p className="text-sm text-gray-600 mb-4">
                  Customize AI analysis prompts
                </p>
                <button className="w-full bg-orange-600 text-white py-2 rounded-md hover:bg-orange-700 transition-colors">
                  Manage Prompts
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
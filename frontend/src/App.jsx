import React, { useState, useEffect } from 'react';
import { Upload, FileText, Shield, User, LogOut, Settings, Zap } from 'lucide-react';
import Login from './components/auth/Login';
import Register from './components/auth/Register';
import ModeSwitcher from './components/common/ModeSwitcher';
import FileUpload from './components/upload/FileUpload';
import useAuthStore from './stores/authStore';
import './App.css';

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [authMode, setAuthMode] = useState('login'); 
  const [selectedProject, setSelectedProject] = useState(null);
  
  const { user, isAuthenticated, logout, initializeAuth } = useAuthStore();

  useEffect(() => {
    initializeAuth();
  }, []);

  const handleLogout = async () => {
    await logout();
  };

  const toggleAuthMode = () => {
    setAuthMode(prev => prev === 'login' ? 'register' : 'login');
  };

  const navigateToUpload = () => setCurrentPage('upload');
  const navigateToReports = () => setCurrentPage('reports');
  const navigateToDashboard = () => setCurrentPage('dashboard');

  // Show authentication if not logged in
  if (!isAuthenticated()) {
    return authMode === 'login' ? 
      <Login onToggleMode={toggleAuthMode} /> : 
      <Register onToggleMode={toggleAuthMode} />;
  }

  const renderPage = () => {
    switch(currentPage) {
      case 'upload':
        return <UploadPage user={user} />;
      case 'reports':
        return <ReportsPage user={user} />;
      case 'profile':
        return <ProfilePage user={user} />;
      default:
        return <DashboardPage user={user} />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Shield className="h-8 w-8 text-blue-600" />
              <h1 className="text-2xl font-bold text-gray-900">AuditSmart</h1>
            </div>
            
            <nav className="flex items-center space-x-4">
              <button 
                onClick={() => setCurrentPage('dashboard')}
                className={`px-3 py-2 rounded-md ${currentPage === 'dashboard' ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900'}`}
              >
                Dashboard
              </button>
              <button 
                onClick={() => setCurrentPage('upload')}
                className={`px-3 py-2 rounded-md ${currentPage === 'upload' ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900'}`}
              >
                Upload
              </button>
              <button 
                onClick={() => setCurrentPage('reports')}
                className={`px-3 py-2 rounded-md ${currentPage === 'reports' ? 'bg-blue-100 text-blue-700' : 'text-gray-600 hover:text-gray-900'}`}
              >
                Reports
              </button>
              
              {/* Mode Switcher */}
              <div className="border-l pl-4">
                <ModeSwitcher />
              </div>
              
              {/* User menu */}
              <div className="flex items-center space-x-3 border-l pl-4">
                <div className="flex items-center space-x-2">
                  {user?.user_mode === 'auditor' ? (
                    <Shield className="h-5 w-5 text-purple-600" />
                  ) : (
                    <User className="h-5 w-5 text-blue-600" />
                  )}
                  <span className="text-sm text-gray-700">{user?.full_name || user?.email}</span>
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    user?.user_mode === 'auditor' 
                      ? 'bg-purple-100 text-purple-800' 
                      : 'bg-blue-100 text-blue-800'
                  }`}>
                    {user?.user_mode === 'auditor' ? 'Auditor' : 'Normal'}
                  </span>
                </div>
                <button
                  onClick={handleLogout}
                  className="flex items-center space-x-1 text-gray-600 hover:text-red-600 px-2 py-1 rounded-md hover:bg-gray-100"
                >
                  <LogOut className="h-4 w-4" />
                  <span className="text-sm">Logout</span>
                </button>
              </div>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {renderPage()}
      </main>
    </div>
  );
}

// Mode-aware Dashboard
function DashboardPage({ user }) {
  const isAuditorMode = user?.user_mode === 'auditor';

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-3xl font-bold text-gray-900">
          Welcome back, {user?.full_name}!
        </h2>
        <div className={`px-4 py-2 rounded-lg ${
          isAuditorMode 
            ? 'bg-purple-100 text-purple-800' 
            : 'bg-blue-100 text-blue-800'
        }`}>
          <div className="flex items-center gap-2">
            {isAuditorMode ? (
              <Shield className="w-5 h-5" />
            ) : (
              <User className="w-5 h-5" />
            )}
            <span className="font-medium">
              {isAuditorMode ? 'Auditor Mode' : 'Normal Mode'}
            </span>
          </div>
        </div>
      </div>
      
      {/* Common Features */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <div className="card hover:shadow-lg transition-shadow cursor-pointer">
          <div className="flex items-center">
            <Upload className="h-8 w-8 text-blue-500 mr-3" />
            <div>
              <h3 className="text-lg font-semibold">Upload Contract</h3>
              <p className="text-gray-600">Upload your smart contract for analysis</p>
            </div>
          </div>
        </div>
        
        <div className="card hover:shadow-lg transition-shadow cursor-pointer">
          <div className="flex items-center">
            <FileText className="h-8 w-8 text-green-500 mr-3" />
            <div>
              <h3 className="text-lg font-semibold">View Reports</h3>
              <p className="text-gray-600">Check your audit reports</p>
            </div>
          </div>
        </div>
        
        <div className="card hover:shadow-lg transition-shadow cursor-pointer">
          <div className="flex items-center">
            <Shield className="h-8 w-8 text-purple-500 mr-3" />
            <div>
              <h3 className="text-lg font-semibold">Security Score</h3>
              <p className="text-gray-600">Current security rating</p>
            </div>
          </div>
        </div>
      </div>

      {/* Auditor-only Features */}
      {isAuditorMode && (
        <div>
          <h3 className="text-xl font-bold text-gray-900 mb-4">Advanced Auditor Tools</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="card bg-purple-50 border-purple-200 hover:shadow-lg transition-shadow cursor-pointer">
              <div className="flex items-center">
                <Settings className="h-8 w-8 text-purple-600 mr-3" />
                <div>
                  <h3 className="text-lg font-semibold text-purple-900">Analysis Configuration</h3>
                  <p className="text-purple-700">Configure advanced static analysis options</p>
                </div>
              </div>
            </div>
            
            <div className="card bg-purple-50 border-purple-200 hover:shadow-lg transition-shadow cursor-pointer">
              <div className="flex items-center">
                <Zap className="h-8 w-8 text-purple-600 mr-3" />
                <div>
                  <h3 className="text-lg font-semibold text-purple-900">Custom Prompts</h3>
                  <p className="text-purple-700">Customize AI analysis prompts</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Recent Activity */}
      <div className="mt-8">
        <h3 className="text-xl font-bold text-gray-900 mb-4">Recent Activity</h3>
        <div className="card">
          <p className="text-gray-600">No recent activity. Start by uploading a contract!</p>
        </div>
      </div>
    </div>
  );
}

function UploadPage({ user }) {
  const isAuditorMode = user?.user_mode === 'auditor';

  return (
    <div>
      <h2 className="text-3xl font-bold text-gray-900 mb-6">Upload Smart Contract</h2>
      
      {isAuditorMode && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-6">
          <h3 className="font-semibold text-purple-900 mb-2">Auditor Mode</h3>
          <p className="text-purple-700 text-sm">
            You have access to advanced analysis features and can view detailed vulnerability reports.
          </p>
        </div>
      )}
      
      <FileUpload />
    </div>
  );
}

function ReportsPage({ user }) {
  return (
    <div>
      <h2 className="text-3xl font-bold text-gray-900 mb-6">Audit Reports</h2>
      <div className="card">
        <p className="text-gray-600">No reports available yet. Upload a contract to get started!</p>
      </div>
    </div>
  );
}

function ProfilePage({ user }) {
  return (
    <div>
      <h2 className="text-3xl font-bold text-gray-900 mb-6">Profile</h2>
      <div className="card">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Email</label>
            <p className="mt-1 text-sm text-gray-900">{user?.email}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Full Name</label>
            <p className="mt-1 text-sm text-gray-900">{user?.full_name}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">User Mode</label>
            <p className="mt-1 text-sm text-gray-900 capitalize">{user?.user_mode}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Member Since</label>
            <p className="mt-1 text-sm text-gray-900">
              {new Date(user?.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function ProjectList({ onSelectProject }) {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const { token } = useAuthStore();

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const response = await fetch('/api/upload/projects', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setProjects(data);
      }
    } catch (error) {
      console.error('Error fetching projects:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="card">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded w-5/6"></div>
          </div>
        </div>
      </div>
    );
  }

  if (projects.length === 0) {
    return (
      <div className="card">
        <p className="text-gray-600">No projects available yet. Upload a contract to get started!</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {projects.map(project => (
        <div key={project.id} className="card hover:shadow-lg transition-shadow cursor-pointer" onClick={() => onSelectProject(project)}>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">{project.name}</h3>
              <p className="text-sm text-gray-600">{project.original_filename}</p>
              <p className="text-xs text-gray-500">
                Created: {new Date(project.created_at).toLocaleDateString()}
              </p>
            </div>
            <div className="text-right">
              <span className={`inline-block px-2 py-1 text-xs font-medium rounded-full ${
                project.status === 'completed' ? 'bg-green-100 text-green-800' :
                project.status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
                project.status === 'failed' ? 'bg-red-100 text-red-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                {project.status}
              </span>
              <p className="text-xs text-gray-500 mt-1">
                {(project.file_size / 1024).toFixed(1)} KB
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// Project Detail Component
function ProjectDetail({ project, onBack }) {
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const { token } = useAuthStore();

  useEffect(() => {
    fetchAnalyses();
  }, [project.id]);

  const fetchAnalyses = async () => {
    try {
      const response = await fetch(`/api/analysis/project/${project.id}/analyses`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setAnalyses(data);
      }
    } catch (error) {
      console.error('Error fetching analyses:', error);
    } finally {
      setLoading(false);
    }
  };

  const viewReport = async (analysisId) => {
    try {
      const response = await fetch(`/api/analysis/analysis/${analysisId}/report`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const htmlContent = await response.text();
        // Open in new window
        const newWindow = window.open();
        newWindow.document.write(htmlContent);
      }
    } catch (error) {
      console.error('Error viewing report:', error);
    }
  };

  return (
    <div>
      <button onClick={onBack} className="mb-4 text-blue-600 hover:text-blue-800">
        ← Back to Projects
      </button>

      <div className="card mb-6">
        <h3 className="text-xl font-semibold text-gray-900 mb-4">{project.name}</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="font-medium text-gray-700">File:</span>
            <p>{project.original_filename}</p>
          </div>
          <div>
            <span className="font-medium text-gray-700">Size:</span>
            <p>{(project.file_size / 1024).toFixed(1)} KB</p>
          </div>
          <div>
            <span className="font-medium text-gray-700">Type:</span>
            <p>{project.project_type}</p>
          </div>
          <div>
            <span className="font-medium text-gray-700">Status:</span>
            <span className={`inline-block px-2 py-1 text-xs font-medium rounded-full ${
              project.status === 'completed' ? 'bg-green-100 text-green-800' :
              project.status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
              project.status === 'failed' ? 'bg-red-100 text-red-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {project.status}
            </span>
          </div>
        </div>
        {project.description && (
          <div className="mt-4">
            <span className="font-medium text-gray-700">Description:</span>
            <p className="text-gray-600">{project.description}</p>
          </div>
        )}
      </div>

      <h4 className="text-lg font-semibold text-gray-900 mb-4">Analysis Reports</h4>
      
      {loading ? (
        <div className="card">
          <div className="animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
            <div className="space-y-3">
              <div className="h-4 bg-gray-200 rounded"></div>
              <div className="h-4 bg-gray-200 rounded w-5/6"></div>
            </div>
          </div>
        </div>
      ) : analyses.length === 0 ? (
        <div className="card">
          <p className="text-gray-600">No analysis reports available for this project.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {analyses.map(analysis => (
            <div key={analysis.id} className="card">
              <div className="flex items-center justify-between">
                <div>
                  <h5 className="font-semibold text-gray-900">
                    Analysis Report
                  </h5>
                  <p className="text-sm text-gray-600">
                    {analysis.summary.total} issues found
                    {analysis.completed_at && ` • ${new Date(analysis.completed_at).toLocaleDateString()}`}
                  </p>
                  <div className="flex space-x-4 mt-2 text-xs">
                    <span className="text-red-600">High: {analysis.summary.high}</span>
                    <span className="text-orange-600">Medium: {analysis.summary.medium}</span>
                    <span className="text-yellow-600">Low: {analysis.summary.low}</span>
                    <span className="text-blue-600">Info: {analysis.summary.informational}</span>
                  </div>
                </div>
                <div className="flex space-x-2">
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    analysis.status === 'completed' ? 'bg-green-100 text-green-800' :
                    analysis.status === 'running' ? 'bg-yellow-100 text-yellow-800' :
                    analysis.status === 'failed' ? 'bg-red-100 text-red-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {analysis.status}
                  </span>
                  {analysis.status === 'completed' && analysis.report_available && (
                    <button
                      onClick={() => viewReport(analysis.id)}
                      className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700"
                    >
                      View Report
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;
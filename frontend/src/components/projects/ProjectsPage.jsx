import React, { useState, useEffect } from 'react';
import ProjectService from '../../services/projectService';
import useAuthStore from '../../stores/authStore';
import ProjectDetail from './ProjectDetail';
import SourceCodeViewer from './SourceCodeViewer';
import AnalysisManager from '../AnalysisManager';

const ProjectsPage = () => {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [currentView, setCurrentView] = useState('list'); // list, detail, source, analysis
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const { token, user } = useAuthStore();
  const isAuditor = user?.user_mode === 'auditor';

  useEffect(() => {
    if (token) {
      fetchProjects();
    }
  }, [token]);

  const fetchProjects = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('Fetching projects with token:', token ? 'Token exists' : 'No token');
      
      const data = await ProjectService.getProjects(token);
      console.log('Projects fetched:', data);
      
      setProjects(data);
    } catch (error) {
      console.error('Error fetching projects:', error);
      setError('Failed to fetch projects: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleProjectSelect = async (project) => {
    try {
      console.log('Selecting project:', project.id);
      const detail = await ProjectService.getProjectDetail(project.id, token);
      console.log('Project detail:', detail);
      
      setSelectedProject(detail);
      setCurrentView('detail');
    } catch (error) {
      console.error('Error fetching project detail:', error);
      setError('Failed to fetch project detail: ' + error.message);
    }
  };

  const renderProjectList = () => (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-3xl font-bold text-gray-900">Projects</h2>
        {isAuditor && (
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
            <span className="text-purple-800 text-sm font-medium">Auditor Mode</span>
          </div>
        )}
      </div>

      {loading ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="card animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-1/4 mb-2"></div>
              <div className="h-3 bg-gray-200 rounded w-1/2"></div>
            </div>
          ))}
        </div>
      ) : projects.length === 0 ? (
        <div className="card text-center py-8">
          <p className="text-gray-600">No projects found. Upload a contract to get started!</p>
        </div>
      ) : (
        <div className="space-y-4">
          {projects.map(project => (
            <div 
              key={project.id} 
              className="card hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => handleProjectSelect(project)}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {project.name}
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600">
                    <div>
                      <span className="font-medium">File:</span> {project.original_filename}
                    </div>
                    <div>
                      <span className="font-medium">Type:</span> {project.project_type}
                    </div>
                    <div>
                      <span className="font-medium">Size:</span> {(project.file_size / 1024).toFixed(1)} KB
                    </div>
                    <div>
                      <span className="font-medium">Created:</span> {new Date(project.created_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
                <div className="ml-4 text-right">
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
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const renderProjectDetail = () => (
    <ProjectDetail 
      project={selectedProject}
      onBack={() => setCurrentView('list')}
      onViewSource={() => setCurrentView('source')}
      onViewAnalysis={() => setCurrentView('analysis')}
      isAuditor={isAuditor}
    />
  );

  const renderSourceView = () => (
    <SourceCodeViewer 
      project={selectedProject}
      onBack={() => setCurrentView('detail')}
    />
  );

  const renderAnalysisView = () => (
    <AnalysisManager 
      project={selectedProject}
      onBack={() => setCurrentView('detail')}
      isAuditor={isAuditor}
    />
  );

  if (error) {
    return (
      <div className="card bg-red-50 border-red-200">
        <p className="text-red-600">{error}</p>
        <button 
          onClick={() => {setError(null); fetchProjects();}}
          className="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {currentView === 'list' && renderProjectList()}
      {currentView === 'detail' && renderProjectDetail()}
      {currentView === 'source' && renderSourceView()}
      {currentView === 'analysis' && renderAnalysisView()}
    </div>
  );
};

export default ProjectsPage;
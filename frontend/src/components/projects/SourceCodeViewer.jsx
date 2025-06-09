import React, { useState, useEffect } from 'react';
import ProjectService from '../../services/projectService';
import { useAuthStore } from '../../stores/authStore';

const SourceCodeViewer = ({ project, onBack }) => {
  const [sourceData, setSourceData] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(true);
  const { token } = useAuthStore();

  useEffect(() => {
    fetchSourceCode();
  }, [project.id]);

  const fetchSourceCode = async (filePath = null) => {
    try {
      setLoading(true);
      const data = await ProjectService.getProjectSource(project.id, filePath, token);
      setSourceData(data);
      if (filePath) {
        setSelectedFile(filePath);
      }
    } catch (error) {
      console.error('Error fetching source code:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (filePath) => {
    fetchSourceCode(filePath);
  };

  return (
    <div>
      <button 
        onClick={onBack}
        className="mb-4 text-blue-600 hover:text-blue-800 flex items-center"
      >
        ← Back to Project
      </button>

      <div className="card">
        <h3 className="text-xl font-semibold text-gray-900 mb-4">Source Code</h3>
        
        {loading ? (
          <div className="animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
            <div className="h-64 bg-gray-200 rounded"></div>
          </div>
        ) : (
          <div>
            {/* File Tree for Foundry Projects */}
            {project.project_type === 'foundry_project' && sourceData.available_files && (
              <div className="mb-4">
                <h4 className="font-medium text-gray-700 mb-2">Available Files:</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                  {sourceData.available_files.map(file => (
                    <button
                      key={file}
                      onClick={() => handleFileSelect(file)}
                      className={`text-left p-2 text-sm rounded hover:bg-blue-50 ${
                        selectedFile === file ? 'bg-blue-100 text-blue-800' : 'text-gray-700'
                      }`}
                    >
                      {file}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Source Code Display */}
            {sourceData.source_code ? (
              <div>
                <div className="flex justify-between items-center mb-2">
                  <h4 className="font-medium text-gray-700">
                    {sourceData.file_path || project.original_filename}
                  </h4>
                  <div className="flex items-center space-x-2">
                    <span className="text-sm text-gray-500">
                      {sourceData.source_code.length} characters
                    </span>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(sourceData.source_code);
                        alert('Source code copied to clipboard!');
                      }}
                      className="px-2 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700"
                    >
                      Copy Code
                    </button>
                  </div>
                </div>
                <div className="bg-gray-50 border rounded-lg overflow-hidden">
                  <div className="p-3 bg-gray-800 text-gray-100 border-b">
                    <span className="text-sm font-medium">Solidity Source Code</span>
                  </div>
                  <div className="overflow-x-auto">
                    <pre className="p-4 text-sm text-left whitespace-pre-wrap bg-gray-50">
                      <code className="language-solidity">
                        {sourceData.source_code}
                      </code>
                    </pre>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-gray-600 text-left">
                {project.project_type === 'foundry_project' 
                  ? 'Select a file to view its source code'
                  : 'No source code available'
                }
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default SourceCodeViewer;
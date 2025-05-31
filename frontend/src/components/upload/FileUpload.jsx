import React, { useState } from 'react';
import { Upload, FileText, AlertCircle, CheckCircle, X, Zap, Download, Eye } from 'lucide-react';
import useAuthStore from '../../stores/authStore';

const FileUpload = ({ user, onNavigateToReports }) => {
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(null);
  const [error, setError] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    file: null,
    solidityVersion: '^0.8.0'
  });

  const { token } = useAuthStore();
  const isNormalUser = user?.user_mode !== 'auditor';

  // Supported Solidity versions for single file upload
  const SUPPORTED_SOLC_VERSIONS = [
    "^0.8.0", "^0.8.21", "^0.8.22", "^0.8.23", "0.8.24", "0.8.25", "0.8.26"
  ];

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    const files = e.dataTransfer.files;
    if (files && files[0]) {
      handleFileSelect(files[0]);
    }
  };

  const handleFileSelect = (file) => {
    // Validate file type
    const allowedTypes = ['.sol', '.zip'];
    const fileExt = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!allowedTypes.includes(fileExt)) {
      setError('Only .sol and .zip files are allowed');
      return;
    }

    // Validate file size (50MB)
    if (file.size > 50 * 1024 * 1024) {
      setError('File size must be less than 50MB');
      return;
    }

    // AUTO-DETECT SOLIDITY VERSION for .sol files
    if (fileExt === '.sol') {
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target.result;
        const pragmaMatch = content.match(/pragma\s+solidity\s+([^;]+);/i);
        if (pragmaMatch) {
          const detectedVersion = pragmaMatch[1].trim();
          setFormData(prev => ({
            ...prev,
            solidityVersion: detectedVersion
          }));
        }
      };
      reader.readAsText(file);
    }

    setError(null);
    setFormData(prev => ({
      ...prev,
      file: file,
      name: prev.name || file.name.split('.')[0] // Auto-fill name if empty
    }));
  };

  const handleFileInput = (e) => {
    const file = e.target.files[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.file) {
      setError('Please select a file');
      return;
    }

    if (!formData.name.trim()) {
      setError('Please enter a project name');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const uploadData = new FormData();
      uploadData.append('file', formData.file);
      uploadData.append('name', formData.name);
      if (formData.description) {
        uploadData.append('description', formData.description);
      }

      const response = await fetch('/api/upload/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: uploadData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const result = await response.json();
      setUploadSuccess(result);
      
      // Reset form
      setFormData({
        name: '',
        description: '',
        file: null,
        solidityVersion: '^0.8.0'
      });

      // Reset file input
      const fileInput = document.querySelector('input[type="file"]');
      if (fileInput) {
        fileInput.value = '';
      }

    } catch (error) {
      console.error('Upload error:', error);
      setError(error.message);
    } finally {
      setUploading(false);
    }
  };

// Start Auto Analysis
  const startAnalysis = async () => {
    if (!uploadSuccess?.project?.id) return;

    setAnalyzing(true);
    setError(null);

    try {
      const response = await fetch(`/api/analysis/analyze/${uploadSuccess.project.id}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Analysis failed');
      }

      const result = await response.json();
      setAnalysisResult(result);

    } catch (error) {
      console.error('Analysis error:', error);
      setError(error.message);
    } finally {
      setAnalyzing(false);
    }
  };

  // Download Report
  const downloadReport = async () => {
    if (!analysisResult?.id) return;

    try {
      const response = await fetch(`/api/analysis/analysis/${analysisResult.id}/report`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const htmlContent = await response.text();
        const blob = new Blob([htmlContent], { type: 'text/html' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `analysis-report-${uploadSuccess.project.name}.html`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (error) {
      console.error('Download error:', error);
    }
  };

  // View Report
  const viewReport = async () => {
    if (!analysisResult?.id) return;

    try {
      const response = await fetch(`/api/analysis/analysis/${analysisResult.id}/report`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const htmlContent = await response.text();
        const newWindow = window.open();
        newWindow.document.write(htmlContent);
      }
    } catch (error) {
      console.error('View report error:', error);
    }
  };

  const removeFile = () => {
    setFormData(prev => ({ ...prev, file: null }));
    setError(null);
    
    // Reset file input
    const fileInput = document.querySelector('input[type="file"]');
    if (fileInput) {
      fileInput.value = '';
    }
  };

  const resetUpload = () => {
    setUploadSuccess(null);
    setAnalysisResult(null);
    setError(null);
  };

  // SUCCESS STATE WITH ANALYSIS OPTIONS
  if (uploadSuccess) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-green-50 border border-green-200 rounded-lg p-6">
          <div className="text-center mb-4">
            <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-green-900 mb-2">
              Upload Successful!
            </h3>
            <p className="text-green-700 mb-4">
              {uploadSuccess.message}
            </p>
          </div>

          <div className="bg-white rounded-md p-4 mb-4">
            <h4 className="font-medium text-gray-900 mb-2">Project Details:</h4>
            <ul className="text-sm text-gray-600 space-y-1">
              {/* <li><span className="font-medium">ID:</span> {uploadSuccess.project.id}</li> */}
              <li><span className="font-medium">Name:</span> {uploadSuccess.project.name}</li>
              <li><span className="font-medium">Type:</span> {uploadSuccess.project.project_type}</li>
              {/* <li><span className="font-medium">Status:</span> {uploadSuccess.project.status}</li> */}
              <li><span className="font-medium">Size:</span> {(uploadSuccess.project.file_size / 1024).toFixed(1)} KB</li>
              <li><span className="font-medium">File:</span> {uploadSuccess.project.original_filename}</li>
              {/* <li><span className="font-medium">Original File:</span> {uploadSuccess.project.original_filename}</li> */}
            </ul>
          </div>
          
          {/* ANALYSIS SECTION FOR NORMAL USERS */}
          {isNormalUser && uploadSuccess.project.project_type === 'single_file' && (
            <div className="bg-blue-50 border border-blue-200 rounded-md p-4 mb-4">
              <h4 className="font-medium text-blue-900 mb-2 flex items-center">
                <Zap className="h-4 w-4 mr-2" />
                Auto Analysis
              </h4>
              
              {!analysisResult ? (
                <div>
                  <p className="text-blue-700 text-sm mb-3">
                    Your contract is ready for automatic security analysis. This will check for common vulnerabilities and provide detailed recommendations.
                  </p>
                  <button
                    onClick={startAnalysis}
                    disabled={analyzing}
                    className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {analyzing ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                        Analyzing Contract...
                      </>
                    ) : (
                      <>
                        <Zap className="h-4 w-4" />
                        Start Auto Analysis
                      </>
                    )}
                  </button>
                </div>
              ) : (
                <div>
                  <p className="text-blue-700 text-sm mb-3">
                    ✅ Analysis completed! Found {analysisResult.summary.total} issues.
                  </p>
                  
                  {/* Vulnerability Summary */}
                  <div className="grid grid-cols-4 gap-2 mb-3 text-xs">
                    <div className="bg-red-100 text-red-800 p-2 rounded text-center">
                      <div className="font-bold">{analysisResult.summary.high}</div>
                      <div>High</div>
                    </div>
                    <div className="bg-orange-100 text-orange-800 p-2 rounded text-center">
                      <div className="font-bold">{analysisResult.summary.medium}</div>
                      <div>Medium</div>
                    </div>
                    <div className="bg-yellow-100 text-yellow-800 p-2 rounded text-center">
                      <div className="font-bold">{analysisResult.summary.low}</div>
                      <div>Low</div>
                    </div>
                    <div className="bg-blue-100 text-blue-800 p-2 rounded text-center">
                      <div className="font-bold">{analysisResult.summary.informational}</div>
                      <div>Info</div>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={downloadReport}
                      className="flex-1 bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 flex items-center justify-center gap-2"
                    >
                      <Download className="h-4 w-4" />
                      Download Report
                    </button>
                    <button
                      onClick={viewReport}
                      className="flex-1 bg-purple-600 text-white py-2 px-4 rounded-md hover:bg-purple-700 flex items-center justify-center gap-2"
                    >
                      <Eye className="h-4 w-4" />
                      View Report
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ERROR DISPLAY */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-4 flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0" />
              <span className="text-sm text-red-700">{error}</span>
            </div>
          )}

          {/* ACTION BUTTONS */}
          <div className="flex gap-3">
            <button
              onClick={resetUpload}
              className="flex-1 bg-gray-600 text-white py-2 px-4 rounded-md hover:bg-gray-700"
            >
              Upload Another File
            </button>
            <button
              onClick={onNavigateToReports}
              className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700"
            >
              View All Reports
            </button>
          </div>


          {/* <div className="mt-4 space-x-3">
            <button
              onClick={() => setUploadSuccess(null)}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
            >
              Upload Another File
            </button>
            <button
              onClick={() => {
                // Navigate to project view hoặc analysis
                console.log('View project:', uploadSuccess.project.id);
              }}
              className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700"
            >
              View Project
            </button>
          </div> */}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Project Info */}
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h3 className="text-lg font-semibold mb-4">Project Information</h3>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Project Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Enter project name"
                maxLength="100"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description (Optional)
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                rows="3"
                placeholder="Brief description of your project"
                maxLength="500"
              />
            </div>

            {/* Solidity Version Selection for .sol files */}
            {formData.file && formData.file.name.endsWith('.sol') && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Solidity Version <span className="text-red-500">*</span>
                </label>
                <select
                  value={formData.solidityVersion}
                  onChange={(e) => setFormData(prev => ({ ...prev, solidityVersion: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                >
                  {SUPPORTED_SOLC_VERSIONS.map(version => (
                    <option key={version} value={version}>
                      {version}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  Version detected from pragma statement. Change if needed for analysis compatibility.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* File Upload */}
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          <h3 className="text-lg font-semibold mb-4">Upload File</h3>
          
          {!formData.file ? (
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                dragActive 
                  ? 'border-blue-500 bg-blue-50' 
                  : 'border-gray-300 hover:border-gray-400'
              }`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-lg font-medium text-gray-900 mb-2">
                Drop your file here
              </p>
              <p className="text-sm text-gray-600 mb-4">
                Supports .sol files and .zip archives (max 50MB)
                {isNormalUser && (
                  <span>
                    <br />
                    <span className="text-blue-600 font-medium">Normal users: .sol files get auto-analysis</span>
                  </span>
                )}
              </p>
              <label className="inline-block bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 cursor-pointer">
                Choose File
                <input
                  type="file"
                  accept=".sol,.zip"
                  onChange={handleFileInput}
                  className="hidden"
                />
              </label>
            </div>
          ) : (
            <div className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <FileText className="h-8 w-8 text-blue-500" />
                  <div>
                    <p className="font-medium text-gray-900">{formData.file.name}</p>
                    <p className="text-sm text-gray-600">
                      {(formData.file.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={removeFile}
                  className="text-red-500 hover:text-red-700"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4 flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0" />
            <span className="text-sm text-red-700">{error}</span>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={uploading || !formData.file || !formData.name.trim()}
          className="w-full bg-blue-600 text-white py-3 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {uploading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              Uploading...
            </>
          ) : (
            <>
              <Upload className="h-4 w-4" />
              Upload Contract
            </>
          )}
        </button>
      </form>
    </div>
  );
};

export default FileUpload;
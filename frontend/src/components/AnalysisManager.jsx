import { useState, useEffect } from 'react';
import ProjectService from '../services/projectService';
import { useAuthStore } from '../stores/authStore';

const AnalysisManager = ({ project, onBack, isAuditor }) => {
  const [currentStep, setCurrentStep] = useState('configure'); // configure, static, edit, ai, report
  const [analyses, setAnalyses] = useState([]);
  const [activeAnalysis, setActiveAnalysis] = useState(null);
  const [staticResults, setStaticResults] = useState(null);
  const [editableResults, setEditableResults] = useState(null);
  const [detectors, setDetectors] = useState(null);
  const [projectStructure, setProjectStructure] = useState(null);
  const [viewMode, setViewMode] = useState('parsed');

  const [slitherOptions, setSlitherOptions] = useState({
    target_files: [],
    detectors: [],
    exclude_detectors: [],
    exclude_dependencies: true,
    exclude_informational: false,
    exclude_optimization: false,
    exclude_low: false
  });

  const [loading, setLoading] = useState(false);
  const { token } = useAuthStore();

  const isFoundryProject = project.project_type === 'foundry_project';

  useEffect(() => {
    if (isAuditor) {
      fetchDetectors();
      fetchAnalyses();
      
      if (isFoundryProject) {
        fetchProjectStructure();
      }
    }
  }, [project.id, isAuditor]);

  const fetchProjectStructure = async () => {
    if (!isFoundryProject || !activeAnalysis) return;
    
    try {
      const structure = await ProjectService.getProjectStructure(activeAnalysis.id, token);
      setProjectStructure(structure);
      
      // Auto-populate target files with recommended targets
      if (structure.structure?.source_files) {
        setSlitherOptions(prev => ({
          ...prev,
          target_files: structure.structure.source_files
        }));
      }
    } catch (error) {
      console.error('Error fetching project structure:', error);
    }
  };

  const fetchDetectors = async () => {
    try {
      const data = await ProjectService.getAvailableDetectors(token);
      setDetectors(data);
    } catch (error) {
      console.error('Error fetching detectors:', error);
    }
  };

  const fetchAnalyses = async () => {
    try {
      const data = await ProjectService.getProjectAnalyses(project.id, token);
      setAnalyses(data);
    } catch (error) {
      console.error('Error fetching analyses:', error);
    }
  };

  const handleStaticAnalysis = async () => {
    try {
      setLoading(true);
      const result = await ProjectService.performStaticAnalysis(
        project.id, 
        slitherOptions, 
        token, 
        project.project_type
      );
      setActiveAnalysis(result);
      setCurrentStep('static');
      fetchAnalyses();

      if (isFoundryProject) {
        // Fetch project structure after analysis
        fetchProjectStructure();
      }
    } catch (error) {
      alert('Static analysis failed: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleViewStaticResults = async (analysisId) => {
    try {
      const results = await ProjectService.getStaticResults(analysisId, token);
      setStaticResults(results);
      setEditableResults(JSON.parse(JSON.stringify(results.parsed_results)));
    } catch (error) {
      alert('Failed to fetch static results: ' + error.message);
    }
  };

  const handleEditResults = () => {
    if (activeAnalysis) {
      handleViewStaticResults(activeAnalysis.id);
      setCurrentStep('edit');
    }
  };

  const handleSaveModifications = async () => {
    if (!activeAnalysis) return;

    try {
      setLoading(true);
      await ProjectService.modifyResults(
        activeAnalysis.id, 
        {
          vulnerabilities: editableResults.vulnerabilities,
          summary: editableResults.summary,
          modification_note: "Auditor modifications applied"
        }, 
        token
      );
      
      alert('Modifications saved successfully!');
      setCurrentStep('static');
      fetchAnalyses();
    } catch (error) {
      alert('Failed to save modifications: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAiEnhancement = async () => {
    if (!activeAnalysis) return;
    
    try {
      setLoading(true);
      const result = await ProjectService.performAiEnhancement(activeAnalysis.id, token);
      
      if (result && result.success !== false) {
        setActiveAnalysis(result);
        setCurrentStep('ai');
        fetchAnalyses();
      } else {
        throw new Error(result.error || 'AI enhancement failed');
      }
    } catch (error) {
      alert('AI enhancement failed: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateReport = async () => {
    if (!activeAnalysis) return;
    
    try {
      setLoading(true);
      const result = await ProjectService.generateReport(activeAnalysis.id, 'html', token);
      // setCurrentStep('report');
      // fetchAnalyses();
      // alert('Report generated successfully!');
      if (result && result.success) {
        setCurrentStep('report');
        fetchAnalyses(); // Refresh analyses to show report_available status
        
        // Show success message
        alert('Report generated successfully! You can now download it from the previous analyses section.');
        } else {
          throw new Error(result.message || 'Unknown error occurred');
        }

    } catch (error) {
      alert('Report generation failed: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  if (!isAuditor) {
    return (
      <div className="card bg-yellow-50 border-yellow-200">
        <p className="text-yellow-800">Advanced analysis features are only available in auditor mode.</p>
        <button onClick={onBack} className="mt-2 text-blue-600 hover:text-blue-800">
          ← Back to Project
        </button>
      </div>
    );
  }

  const renderConfigureStep = () => (
    <div className="space-y-6">
      <div>
        <h4 className="font-semibold text-gray-900 mb-3">
          {isFoundryProject ? 'Foundry Project Analysis Configuration' : 'Static Analysis Configuration'}
        </h4>
        
        {/* Project Structure Display for Foundry */}
        {isFoundryProject && (
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <h5 className="font-medium text-blue-900 mb-2">Foundry Project Analysis</h5>
          <p className="text-blue-800 text-sm">
            For Foundry projects, Slither will analyze the entire project automatically. 
            You cannot select specific target files - this ensures complete dependency analysis.
          </p>
        </div>
        )}

        {/* Target Files Selection for Foundry */}
        {/* {isFoundryProject && projectStructure && (
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Target Files (leave empty to analyze all recommended files)
            </label>
            <div className="max-h-40 overflow-y-auto border rounded p-2">
              {projectStructure.structure.source_files?.map((file, index) => (
                <label key={`file-${file}-${index}`} className="flex items-center text-sm py-1">
                  <input
                    type="checkbox"
                    checked={slitherOptions.target_files.includes(file)}
                    onChange={(e) => {
                      const newFiles = e.target.checked
                        ? [...slitherOptions.target_files, file]
                        : slitherOptions.target_files.filter(f => f !== file);
                      setSlitherOptions({...slitherOptions, target_files: newFiles});
                    }}
                    className="mr-2"
                  />
                  <span className={file.includes('test') ? 'text-gray-500' : 'text-gray-900'}>
                    {file}
                    {file.includes('test') && <span className="text-xs text-gray-400 ml-1">(test)</span>}
                  </span>
                </label>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Recommended: Focus on source files, exclude test files
            </p>
          </div>
        )} */}

        {/* Detector Selection */}
        {detectors && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Detectors (leave empty for all)
              </label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2 max-h-40 overflow-y-auto border rounded p-2">
                {/* Remove duplicates and add unique keys */}
                {[...new Set(detectors.available_detectors)].map((detector, index) => (
                  <label key={`detector-${detector}-${index}`} className="flex items-center text-sm">
                    <input
                      type="checkbox"
                      checked={slitherOptions.detectors.includes(detector)}
                      onChange={(e) => {
                        const newDetectors = e.target.checked
                          ? [...slitherOptions.detectors, detector]
                          : slitherOptions.detectors.filter(d => d !== detector);
                        setSlitherOptions({...slitherOptions, detectors: newDetectors});
                      }}
                      className="mr-2"
                    />
                    {detector}
                  </label>
                ))}
              </div>
            </div>

            {/* Enhanced Exclude Options for Foundry */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Exclude Options
              </label>
              <div className="space-y-2">
                {[
                  { key: 'exclude_dependencies', label: 'Exclude Dependencies', default: true, recommended: true },
                  { key: 'exclude_informational', label: 'Exclude Informational', default: false },
                  { key: 'exclude_optimization', label: 'Exclude Optimization', default: false },
                  { key: 'exclude_low', label: 'Exclude Low Severity', default: false }
                ].map(option => (
                  <label key={option.key} className="flex items-center text-sm">
                    <input
                      type="checkbox"
                      checked={slitherOptions[option.key]}
                      onChange={(e) => setSlitherOptions({
                        ...slitherOptions, 
                        [option.key]: e.target.checked
                      })}
                      className="mr-2"
                    />
                    {option.label}
                    {option.recommended && (
                      <span className="ml-2 text-xs text-green-600">(recommended)</span>
                    )}
                  </label>
                ))}
              </div>
            </div>
          </div>
        )}

        <button
          onClick={handleStaticAnalysis}
          disabled={loading}
          className="mt-4 px-6 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:bg-gray-400"
        >
          {loading ? `Running ${isFoundryProject ? 'Foundry' : 'Static'} Analysis...` : `Start ${isFoundryProject ? 'Foundry' : 'Static'} Analysis`}
        </button>
      </div>
    </div>
  );

  const renderStaticStep = () => {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="font-semibold text-gray-900">
            {isFoundryProject ? 'Foundry Analysis Results' : 'Static Analysis Results'}
          </h4>
          <div className="space-x-2">
            {/* <button
              onClick={handleEditResults}
              className="px-4 py-2 bg-yellow-600 text-white text-sm rounded hover:bg-yellow-700"
            >
              Edit Results
            </button> */}

            {activeAnalysis && (
              <button
                onClick={() => handleViewStaticResults(activeAnalysis.id)}
                className="px-4 py-2 bg-gray-600 text-white text-sm rounded hover:bg-gray-700"
              >
                View Raw Results
              </button>
            )}
          </div>
        </div>

        {activeAnalysis && (
          <div className="space-y-4">
            {/* Analysis Summary */}
            <div className="bg-gray-50 border rounded-lg p-4">
              <div className="flex space-x-4 text-sm">
                <span className="text-red-600">High: {activeAnalysis.summary.high}</span>
                <span className="text-orange-600">Medium: {activeAnalysis.summary.medium}</span>
                <span className="text-yellow-600">Low: {activeAnalysis.summary.low}</span>
                <span className="text-blue-600">Info: {activeAnalysis.summary.informational}</span>
              </div>
              <p className="mt-2 text-gray-700">
                Found {activeAnalysis.summary.total} total issues
              </p>
            </div>

            {/* Foundry-specific metadata */}
            {/* {isFoundryProject && projectStructure && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h5 className="font-medium text-blue-900 mb-2">Analysis Scope</h5>
                <div className="text-sm text-blue-800">
                  <p>Analyzed {projectStructure.structure.source_files?.length || 0} files out of {projectStructure.structure.source_files?.length || 0} source files</p>
                  <p>Analysis path: {projectStructure.analysis_path}</p>
                </div>
              </div>
            )} */}
          </div>
        )}

        <div className="flex space-x-3">
          <button
            onClick={handleAiEnhancement}
            disabled={loading || !activeAnalysis}
            className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
          >
            {loading ? 'Processing...' : 'Enhance with AI'}
          </button>
          <button
            onClick={() => setCurrentStep('configure')}
            className="px-6 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
          >
            Reconfigure
          </button>
        </div>

        {/* Enhanced Raw Results Modal with Foundry Support */}
        {staticResults && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
              <div className="flex justify-between items-center p-6 border-b">
                <h3 className="text-lg font-semibold text-gray-900">
                  {isFoundryProject ? 'Foundry Analysis Results' : 'Static Analysis Results'}
                </h3>
                <button
                  onClick={() => setStaticResults(null)}
                  className="text-gray-400 hover:text-gray-600 text-2xl"
                >
                  ×
                </button>
              </div>
              
              <div className="flex-1 overflow-y-auto p-6">
                {/* Foundry Metadata Section */}
                {isFoundryProject && staticResults.parsed_results?.foundry_metadata && (
                  <div className="mb-6">
                    <h4 className="font-medium text-gray-900 mb-3">Foundry Project Metadata</h4>
                    <div className="bg-blue-50 rounded-lg p-4">
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <strong>Original Path:</strong> {staticResults.parsed_results.foundry_metadata.original_file_path}
                        </div>
                        <div>
                          <strong>Analysis Path:</strong> {staticResults.parsed_results.foundry_metadata.extracted_path}
                        </div>
                        <div>
                          <strong>Total Source Files:</strong> {staticResults.parsed_results.foundry_metadata.analysis_scope?.total_source_files || 0}
                        </div>
                        <div>
                          <strong>Analyzed Files:</strong> {staticResults.parsed_results.foundry_metadata.analysis_scope?.analyzed_files || 0}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Tabs for different views */}
                <div className="mb-4">
                  <div className="flex space-x-4 border-b">
                    <button 
                      onClick={() => setViewMode('parsed')}
                      className={`pb-2 px-1 border-b-2 font-medium ${
                        viewMode === 'parsed' 
                          ? 'border-blue-500 text-blue-600' 
                          : 'border-transparent text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      Parsed Results
                    </button>
                    <button 
                      onClick={() => setViewMode('raw')}
                      className={`pb-2 px-1 border-b-2 font-medium ${
                        viewMode === 'raw' 
                          ? 'border-blue-500 text-blue-600' 
                          : 'border-transparent text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      Raw JSON
                    </button>
                  </div>
                </div>

                {/* Conditional View Content */}
                {viewMode === 'parsed' ? (
                  // Parsed Results View (existing code)
                  <div className="space-y-6">
                    {/* Summary */}
                    <div>
                      <h4 className="font-medium text-gray-900 mb-3">Summary</h4>
                      <div className="bg-gray-50 rounded-lg p-4">
                        <div className="grid grid-cols-5 gap-4 text-center">
                          <div>
                            <div className="text-xl font-bold text-gray-900">
                              {staticResults.parsed_results?.summary?.total || 0}
                            </div>
                            <div className="text-sm text-gray-600">Total</div>
                          </div>
                          <div>
                            <div className="text-xl font-bold text-red-600">
                              {staticResults.parsed_results?.summary?.high || 0}
                            </div>
                            <div className="text-sm text-gray-600">High</div>
                          </div>
                          <div>
                            <div className="text-xl font-bold text-orange-600">
                              {staticResults.parsed_results?.summary?.medium || 0}
                            </div>
                            <div className="text-sm text-gray-600">Medium</div>
                          </div>
                          <div>
                            <div className="text-xl font-bold text-yellow-600">
                              {staticResults.parsed_results?.summary?.low || 0}
                            </div>
                            <div className="text-sm text-gray-600">Low</div>
                          </div>
                          <div>
                            <div className="text-xl font-bold text-blue-600">
                              {staticResults.parsed_results?.summary?.informational || 0}
                            </div>
                            <div className="text-sm text-gray-600">Info</div>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Vulnerabilities */}
                    <div>
                      <h4 className="font-medium text-gray-900 mb-3">
                        Vulnerabilities ({staticResults.parsed_results?.vulnerabilities?.length || 0})
                      </h4>
                      {staticResults.parsed_results?.vulnerabilities?.length > 0 ? (
                        <div className="space-y-3">
                          {staticResults.parsed_results.vulnerabilities.map((vuln, index) => (
                            <div key={index} className="border rounded-lg p-4">
                              <div className="flex items-start justify-between">
                                <div className="flex-1">
                                  <h5 className="font-medium text-gray-900">{vuln.title}</h5>
                                  <p className="text-sm text-gray-600 mt-1">{vuln.description}</p>
                                  {/* {vuln.recommendation && (
                                    <p className="text-sm text-blue-600 mt-2">
                                      <strong>Recommendation:</strong> {vuln.recommendation}
                                    </p>
                                  )} */}
                                  {vuln.code_snippet && (
                                    <pre className="text-xs bg-gray-100 p-2 rounded mt-2 overflow-x-auto text-left">
                                      {vuln.code_snippet}
                                    </pre>
                                  )}
                                </div>
                                <span className={`px-2 py-1 text-xs font-medium rounded-full ml-4 ${
                                  vuln.severity === 'HIGH' ? 'bg-red-100 text-red-800' :
                                  vuln.severity === 'MEDIUM' ? 'bg-orange-100 text-orange-800' :
                                  vuln.severity === 'LOW' ? 'bg-yellow-100 text-yellow-800' :
                                  'bg-blue-100 text-blue-800'
                                }`}>
                                  {vuln.severity}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-gray-500 text-center py-8">No vulnerabilities found</p>
                      )}
                    </div>
                  </div>
                ) : (
                  // Raw JSON View
                  <div className="space-y-4">
                    <div>
                      <h4 className="font-medium text-gray-900 mb-3">Complete Raw JSON Response</h4>
                      <div className="bg-gray-900 text-gray-100 rounded-lg overflow-hidden">
                        <div className="p-3 bg-gray-800 border-b border-gray-700">
                          <span className="text-sm font-medium">JSON Response</span>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(JSON.stringify(staticResults, null, 2));
                              alert('JSON copied to clipboard!');
                            }}
                            className="float-right px-2 py-1 bg-gray-600 text-white text-xs rounded hover:bg-gray-500"
                          >
                            Copy JSON
                          </button>
                        </div>
                        <div className="p-4 overflow-x-auto max-h-96">
                          <pre className="text-sm text-left whitespace-pre-wrap">
                            {JSON.stringify(staticResults, null, 2)}
                          </pre>
                        </div>
                      </div>
                    </div>

                    {/* Separate sections for easier reading */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Slither Results */}
                      <div>
                        <h4 className="font-medium text-gray-900 mb-3">Slither Raw Results</h4>
                        <div className="bg-gray-900 text-gray-100 rounded-lg overflow-hidden">
                          <div className="p-3 bg-gray-800 border-b border-gray-700">
                            <span className="text-sm font-medium">slither_results</span>
                          </div>
                          <div className="p-4 overflow-x-auto max-h-64">
                            <pre className="text-xs text-left whitespace-pre-wrap">
                              {JSON.stringify(staticResults.slither_results, null, 2)}
                            </pre>
                          </div>
                        </div>
                      </div>

                      {/* Parsed Results */}
                      <div>
                        <h4 className="font-medium text-gray-900 mb-3">Parsed Results</h4>
                        <div className="bg-gray-900 text-gray-100 rounded-lg overflow-hidden">
                          <div className="p-3 bg-gray-800 border-b border-gray-700">
                            <span className="text-sm font-medium">parsed_results</span>
                          </div>
                          <div className="p-4 overflow-x-auto max-h-64">
                            <pre className="text-xs text-left whitespace-pre-wrap">
                              {JSON.stringify(staticResults.parsed_results, null, 2)}
                            </pre>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className="border-t p-4">
                <button
                  onClick={() => setStaticResults(null)}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderEditStep = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="font-semibold text-gray-900">Edit Static Analysis Results</h4>
        <div className="space-x-2">
          <button
            onClick={handleSaveModifications}
            disabled={loading}
            className="px-4 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:bg-gray-400"
          >
            {loading ? 'Saving...' : 'Save Changes'}
          </button>
          <button
            onClick={() => setCurrentStep('static')}
            className="px-4 py-2 bg-gray-600 text-white text-sm rounded hover:bg-gray-700"
          >
            Cancel
          </button>
        </div>
      </div>

      {editableResults && (
        <div className="space-y-4">
          {/* Summary Editor */}
          <div className="bg-gray-50 border rounded-lg p-4">
            <h5 className="font-medium mb-3">Summary</h5>
            <div className="grid grid-cols-5 gap-4">
              {['total', 'high', 'medium', 'low', 'informational'].map(severity => (
                <div key={severity}>
                  <label className="block text-sm font-medium text-gray-700 capitalize">
                    {severity}
                  </label>
                  <input
                    type="number"
                    value={editableResults.summary[severity]}
                    onChange={(e) => setEditableResults({
                      ...editableResults,
                      summary: {
                        ...editableResults.summary,
                        [severity]: parseInt(e.target.value) || 0
                      }
                    })}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Vulnerabilities Editor */}
          <div className="bg-gray-50 border rounded-lg p-4">
            <h5 className="font-medium mb-3">Vulnerabilities ({editableResults.vulnerabilities.length})</h5>
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {editableResults.vulnerabilities.map((vuln, index) => (
                <div key={index} className="bg-white p-3 border rounded">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Title</label>
                      <input
                        type="text"
                        value={vuln.title}
                        onChange={(e) => {
                          const newVulns = [...editableResults.vulnerabilities];
                          newVulns[index].title = e.target.value;
                          setEditableResults({...editableResults, vulnerabilities: newVulns});
                        }}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Severity</label>
                      <select
                        value={vuln.severity}
                        onChange={(e) => {
                          const newVulns = [...editableResults.vulnerabilities];
                          newVulns[index].severity = e.target.value;
                          setEditableResults({...editableResults, vulnerabilities: newVulns});
                        }}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                      >
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                        <option value="informational">Informational</option>
                      </select>
                    </div>
                  </div>
                  <div className="mt-2">
                    <label className="block text-sm font-medium text-gray-700">Description</label>
                    <textarea
                      value={vuln.description}
                      onChange={(e) => {
                        const newVulns = [...editableResults.vulnerabilities];
                        newVulns[index].description = e.target.value;
                        setEditableResults({...editableResults, vulnerabilities: newVulns});
                      }}
                      rows={2}
                      className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                    />
                  </div>
                  <button
                    onClick={() => {
                      const newVulns = editableResults.vulnerabilities.filter((_, i) => i !== index);
                      setEditableResults({...editableResults, vulnerabilities: newVulns});
                    }}
                    className="mt-2 px-2 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );

  const renderAiStep = () => (
    <div className="space-y-4">
      <h4 className="font-semibold text-gray-900">AI Enhanced Analysis</h4>
      
      {activeAnalysis && (
        <div className={`border rounded-lg p-4 ${
          activeAnalysis.ai_enhanced === false 
            ? 'bg-yellow-50 border-yellow-200' 
            : 'bg-green-50 border-green-200'
        }`}>
          {activeAnalysis.ai_enhanced === false ? (
            <div>
              <p className="text-yellow-800 mb-2">
                ⚠️ AI enhancement encountered issues but static analysis is complete
              </p>
              {activeAnalysis.ai_error && (
                <p className="text-sm text-yellow-700 mb-2">
                  Error: {activeAnalysis.ai_error}
                </p>
              )}
            </div>
          ) : (
            <p className="text-green-800">
              ✅ Analysis enhanced with AI recommendations
            </p>
          )}

          <div className="mt-2 flex space-x-4 text-sm">
            <span className="text-red-600">High: {activeAnalysis.summary.high}</span>
            <span className="text-orange-600">Medium: {activeAnalysis.summary.medium}</span>
            <span className="text-yellow-600">Low: {activeAnalysis.summary.low}</span>
            <span className="text-blue-600">Info: {activeAnalysis.summary.informational}</span>
          </div>

        {/* AI recommendations */}
        {activeAnalysis.ai_recommendations && activeAnalysis.ai_recommendations.length > 0 && (
          <div className="mt-4">
            <h5 className="font-medium text-green-900 mb-2">
              AI Recommendations ({activeAnalysis.ai_recommendations.length})
            </h5>
            {/* <div className="space-y-2 max-h-40 overflow-y-auto">
              {activeAnalysis.ai_recommendations.map((rec, index) => (
                <div key={index} className="bg-white p-3 rounded border border-green-200">
                  <div className="flex items-start">
                    <div className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold mr-3 mt-0.5">
                      AI
                    </div>
                    <p className="text-sm text-green-800 flex-1">{rec}</p>
                  </div>
                </div>
              ))}
            </div>
          </div> */}
            <div className="space-y-2 max-h-40 overflow-y-auto">
                {activeAnalysis.ai_recommendations.map((rec, index) => (
                  <div key={index} className={`p-3 rounded border ${
                    rec.includes('failed') || rec.includes('error')
                      ? 'bg-red-50 border-red-200'
                      : 'bg-white border-green-200'
                  }`}>
                    <div className="flex items-start">
                      <div className={`w-6 h-6 text-white rounded-full flex items-center justify-center text-xs font-bold mr-3 mt-0.5 ${
                        rec.includes('failed') || rec.includes('error')
                          ? 'bg-red-600'
                          : 'bg-blue-600'
                      }`}>
                        {rec.includes('failed') || rec.includes('error') ? '!' : 'AI'}
                      </div>
                      <p className={`text-sm flex-1 ${
                        rec.includes('failed') || rec.includes('error')
                          ? 'text-red-800'
                          : 'text-green-800'
                      }`}>
                        {rec}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
        )}
        
        {/* AI vulnerabilities nếu có */}
        {activeAnalysis.vulnerabilities && activeAnalysis.vulnerabilities.length > 0 && (
          <div className="mt-4">
            <h5 className="font-medium text-green-900 mb-2">
              AI Enhanced Vulnerabilities ({activeAnalysis.vulnerabilities.length})
            </h5>
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {activeAnalysis.vulnerabilities.slice(0, 3).map((vuln, index) => (
                <div key={index} className="bg-white p-3 rounded border border-green-200">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h6 className="font-medium text-gray-900 text-sm">{vuln.title}</h6>
                      <p className="text-xs text-gray-600 mt-1">{vuln.description}</p>
                    </div>
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ml-2 ${
                      vuln.severity === 'HIGH' ? 'bg-red-100 text-red-800' :
                      vuln.severity === 'MEDIUM' ? 'bg-orange-100 text-orange-800' :
                      vuln.severity === 'LOW' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-blue-100 text-blue-800'
                    }`}>
                      {vuln.severity}
                    </span>
                  </div>
                </div>
              ))}
              {activeAnalysis.vulnerabilities.length > 3 && (
                <p className="text-xs text-gray-500 text-center">
                  ...and {activeAnalysis.vulnerabilities.length - 3} more vulnerabilities
                </p>
              )}
            </div>
          </div>
        )}
      </div>
      )}

      <button
        onClick={handleGenerateReport}
        disabled={loading || !activeAnalysis}
        className="px-6 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-400"
      >
        {loading ? 'Generating...' : 'Generate Report'}
      </button>
    </div>
  );

  return (
    <div>
      <button 
        onClick={onBack}
        className="mb-4 text-blue-600 hover:text-blue-800 flex items-center"
      >
        ← Back to Project
      </button>

      <div className="card">
        <h3 className="text-xl font-semibold text-gray-900 mb-6">
          {isFoundryProject ? 'Foundry Project Analysis' : 'Advanced Analysis'}
        </h3>
        
        {/* Step Indicator */}
        <div className="flex items-center space-x-4 mb-6">
          {[
            {key: 'configure', label: isFoundryProject ? 'Configure Slither' : 'Configure' },
            { key: 'static', label: 'Static Analysis' },
            // { key: 'edit', label: 'Edit Results' },
            { key: 'ai', label: 'AI Enhancement' },
            { key: 'report', label: 'Generate Report' }
          ].map((step, index) => (
            <div key={step.key} className="flex items-center">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                currentStep === step.key 
                  ? 'bg-purple-600 text-white' 
                  : 'bg-gray-200 text-gray-600'
              }`}>
                {index + 1}
              </div>
              <span className={`ml-2 text-sm ${
                currentStep === step.key ? 'text-purple-600 font-medium' : 'text-gray-600'
              }`}>
                {step.label}
              </span>
              {index < 4 && <div className="w-8 h-px bg-gray-300 mx-4"></div>}
            </div>
          ))}
        </div>

        {/* Step Content */}
        {currentStep === 'configure' && renderConfigureStep()}
        {currentStep === 'static' && renderStaticStep()}
        {currentStep === 'edit' && renderEditStep()}
        {currentStep === 'ai' && renderAiStep()}
        {currentStep === 'report' && (
          <div className="text-center py-8">
            <div className="text-green-600 text-6xl mb-4">✓</div>
            <h4 className="text-lg font-semibold text-gray-900 mb-2">Report Generated Successfully!</h4>
            <p className="text-gray-600">
              Your {isFoundryProject ? 'Foundry project' : 'analysis'} report has been generated and is ready for download.
            </p>
          </div>
        )}
      </div>

      {/* Previous Analyses */}
      {analyses.length > 0 && (
        <div className="card mt-6">
          <h4 className="text-lg font-semibold text-gray-900 mb-4">Previous Analyses</h4>
          <div className="space-y-3">
            {analyses.map(analysis => (
              <div key={analysis.id} className="border rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <h5 className="font-semibold text-gray-900">
                      Analysis #{analysis.id.slice(-8)}
                    </h5>
                    <p className="text-sm text-gray-600">
                      {analysis.summary.total} issues found
                      {analysis.completed_at && (
                        <span>
                          {' • '}
                          {new Date(analysis.completed_at).toLocaleString('en-US', {
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                            hour12: true
                          })}
                        </span>
                      )}
                    </p>
                    
                    {/* Summary Stats */}
                    <div className="flex space-x-4 mt-2 text-xs">
                      <span className="text-red-600">High: {analysis.summary.high}</span>
                      <span className="text-orange-600">Medium: {analysis.summary.medium}</span>
                      <span className="text-yellow-600">Low: {analysis.summary.low}</span>
                      <span className="text-blue-600">Info: {analysis.summary.informational}</span>
                    </div>
                  </div>
                  
                  {/* Status Badge */}
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                      analysis.status === 'completed' ? 'bg-green-100 text-green-800' :
                      analysis.status === 'running' ? 'bg-yellow-100 text-yellow-800' :
                      analysis.status === 'failed' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {analysis.status}
                    </span>
                    
                    {/* Action Buttons */}
                    <div className="flex space-x-2">
                      {/* Load Analysis Button */}
                      {/* <button
                        onClick={() => setActiveAnalysis(analysis)}
                        className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                        title="Load this analysis as active"
                      >
                        Load
                      </button> */}
                      
                      {/* Static Results Button - Show if slither_results exists */}
                      {analysis.slither_results && (
                        <button
                          onClick={() => handleViewStaticResults(analysis.id)}
                          className="px-3 py-1 bg-gray-600 text-white text-sm rounded hover:bg-gray-700"
                          title="View raw static analysis results"
                        >
                          Static Results
                        </button>
                      )}
                      
                      {/* AI Results Button - Show if AI analysis exists */}
                      {analysis.ai_recommendations && analysis.ai_recommendations.length > 0 && (
                        <button
                          onClick={() => {
                            // Hiển thị AI results trong modal riêng
                            setStaticResults({
                              analysis_id: analysis.id,
                              ai_results: analysis.ai_recommendations,
                              parsed_results: {
                                vulnerabilities: analysis.vulnerabilities || [],
                                summary: analysis.summary,
                                ai_enhanced: true
                              },
                              status: analysis.status,
                              completed_at: analysis.completed_at
                            });
                            setShowStaticModal(true);
                          }}
                          className="px-3 py-1 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700"
                          title="View AI enhanced results"
                        >
                          AI Results
                        </button>
                      )}
                      
                      {/* Report Button - Show if report is available */}
                      {analysis.report_available && (
                        <button
                          onClick={() => ProjectService.viewReport(analysis.id, token)}
                          className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                          title="View generated report"
                        >
                          View Report
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default AnalysisManager;
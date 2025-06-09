import { useState, useEffect } from 'react';
import ProjectService from '../../services/projectService';
import { useAuthStore } from '../../stores/authStore';

const ProjectDetail = ({ project, onBack, onViewSource, onViewAnalysis, isAuditor }) => {
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [staticResults, setStaticResults] = useState(null);
  const [showStaticModal, setShowStaticModal] = useState(false);
  const { token } = useAuthStore();

  useEffect(() => {
    fetchAnalyses();
  }, [project.id]);

  const fetchAnalyses = async () => {
    try {
      const data = await ProjectService.getProjectAnalyses(project.id, token);
      setAnalyses(data);
    } catch (error) {
      console.error('Error fetching analyses:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleStartAnalysis = async () => {
    if (analysisLoading) return;

    setAnalysisLoading(true);
    try {
      await ProjectService.performAutoAnalysis(project.id, token);
      fetchAnalyses(); // Refresh analyses
    } catch (error) {
      alert('Analysis failed: ' + error.message);
    } finally {
      setAnalysisLoading(false);
    }
  };

  const handleViewReport = async (analysisId) => {
    try {
      await ProjectService.viewReport(analysisId, token);
    } catch (error) {
      alert('Failed to view report: ' + error.message);
    }
  };

  const handleViewStaticResults = async (analysisId) => {
    try {
      const results = await ProjectService.getStaticResults(analysisId, token);
      setStaticResults(results);
      setShowStaticModal(true);
    } catch (error) {
      console.error('❌ Failed to fetch static results:', error);
      alert('Failed to view static results: ' + error.message);
    }
  };

  const closeStaticModal = () => {
    setShowStaticModal(false);
    setStaticResults(null);
  };

  return (
    <div>
      <button 
        onClick={onBack}
        className="mb-4 text-blue-600 hover:text-blue-800 flex items-center"
      >
        ← Back to Projects
      </button>

      {/* Project Info */}
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

        {/* Action Buttons */}
        <div className="mt-6 flex flex-wrap gap-3">
          <button
            onClick={onViewSource}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            View Source Code
          </button>
          
          {!isAuditor ? (
            <button
              onClick={handleStartAnalysis}
              disabled={project.status === 'processing'}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-400"
              title={project.project_type === 'foundry_project' 
                ? 'Start automatic Foundry project analysis' 
                : 'Start automatic contract analysis'
              }
            >
              {analysisLoading && (
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              )}
              
              {analysisLoading ? 'Starting Analysis...' :
              project.status === 'processing' ? 'Analyzing...' : 
              project.project_type === 'foundry_project' ? 'Start Foundry Analysis' : 'Start Analysis'}
            </button>
          ) : (
            <>
              <button
                onClick={onViewAnalysis}
                className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700"
              >
                Advanced Analysis
              </button>
            </>
          )}
          {/* Project type indicator */}
          <div className="flex items-center px-3 py-2 bg-gray-100 rounded text-sm text-gray-600">
            <span className="font-medium">Type:</span>
            <span className="ml-1 capitalize">{project.project_type.replace('_', ' ')}</span>
            {project.project_type === 'foundry_project' && !isAuditor && (
              <span className="ml-2 text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                Auto-config enabled
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Recent Analysis */}
      <div className="card">
        <h4 className="text-lg font-semibold text-gray-900 mb-4">Recent Analysis</h4>
        
        {loading ? (
          <div className="animate-pulse space-y-3">
            {[...Array(2)].map((_, i) => (
              <div key={i} className="h-16 bg-gray-200 rounded"></div>
            ))}
          </div>
        ) : analyses.length === 0 ? (
          <p className="text-gray-600">No recent reports available for this project.</p>
        ) : (
          <div className="space-y-4">
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
                          <span className="font-medium">
                            {new Date(analysis.completed_at).toLocaleString('en-US', {
                              year: 'numeric',
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                              hour12: true
                            })}
                          </span>
                        </span>
                      )}
                      {analysis.started_at && analysis.completed_at && (
                        <span className="text-xs text-gray-500 ml-2">
                          (Duration: {Math.round((new Date(analysis.completed_at) - new Date(analysis.started_at)) / 1000)}s)
                        </span>
                      )}
                    </p>
                    
                    {/* Enhanced Summary Stats */}
                    <div className="flex space-x-4 mt-2 text-xs">
                      <span className="text-red-600 font-medium">High: {analysis.summary.high}</span>
                      <span className="text-orange-600 font-medium">Medium: {analysis.summary.medium}</span>
                      <span className="text-yellow-600 font-medium">Low: {analysis.summary.low}</span>
                      <span className="text-blue-600 font-medium">Info: {analysis.summary.informational}</span>
                    </div>
                    
                    {/* Analysis Type & Additional Info */}
                    <div className="flex items-center space-x-3 mt-2 text-xs text-gray-500">
                      <span>Type: {analysis.analysis_type || 'Standard'}</span>
                      {analysis.started_at && (
                        <span>
                          Started: {new Date(analysis.started_at).toLocaleString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </span>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                      analysis.status === 'completed' ? 'bg-green-100 text-green-800' :
                      analysis.status === 'running' ? 'bg-yellow-100 text-yellow-800' :
                      analysis.status === 'failed' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {analysis.status}
                    </span>
                    
                    {/* Buttons for Auditors */}
                    {isAuditor && analysis.status === 'completed' && (
                      <>
                        {/* Static Results Button - ALWAYS show for auditors */}
                        <button
                          onClick={() => handleViewStaticResults(analysis.id)}
                          className="px-3 py-1 bg-gray-600 text-white text-xs rounded hover:bg-gray-700"
                          title="View raw static analysis results"
                        >
                          Static Results
                        </button>
                        
                        {/* AI Results Button - Show if AI analysis exists */}
                        {analysis.ai_recommendations && analysis.ai_recommendations.length > 0 && (
                          <button
                            onClick={() => {
                              // Future: Handle AI results view
                              console.log('AI Results:', analysis.ai_recommendations);
                              // Show AI results in a modal similar to static results
                              setStaticResults({
                                analysis_id: analysis.id,
                                ai_results: analysis.ai_recommendations,
                                parsed_results: {
                                  vulnerabilities: analysis.vulnerabilities || [],
                                  summary: analysis.summary,
                                  ai_enhanced: true,
                                  ai_metadata: {
                                    enhancement_timestamp: analysis.completed_at,
                                    total_recommendations: analysis.ai_recommendations.length,
                                    vulnerabilities_enhanced: analysis.vulnerabilities?.length || 0
                                  }
                                },
                                status: analysis.status,
                                completed_at: analysis.completed_at,
                                display_mode: 'ai_enhanced' // Flag để biết đây là AI results
                              });
                              setShowStaticModal(true);
                            }}
                            className="px-3 py-1 bg-indigo-600 text-white text-xs rounded hover:bg-indigo-700"
                            title="View AI enhanced results"
                          >
                            AI Results
                          </button>
                        )}
                        
                        {analysis.report_available && (
                          <button
                            onClick={() => handleViewReport(analysis.id)}
                            className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700"
                            title="View generated report"
                          >
                            View Report
                          </button>
                        )}
                      </>
                    )}
                    
                    {/* Button for Normal Users */}
                    {!isAuditor && analysis.status === 'completed' && analysis.report_available && (
                      <button
                        onClick={() => handleViewReport(analysis.id)}
                        className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700"
                        title="View analysis report"
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

      {/* Static Results Modal */}
      {showStaticModal && staticResults && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
            <div className="flex justify-between items-center p-6 border-b">
              <h3 className="text-lg font-semibold text-gray-900">
                {staticResults.display_mode === 'ai_enhanced' 
                  ? 'AI Enhanced Analysis Results' 
                  : staticResults.ai_results 
                    ? 'AI Enhanced Analysis Results' 
                    : 'Static Analysis Results'
                }
              </h3>
              <button
                onClick={closeStaticModal}
                className="text-gray-400 hover:text-gray-600 text-2xl"
              >
                ×
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6">
              {/* AI Enhancement Badge */}
              {(staticResults.ai_results || staticResults.display_mode === 'ai_enhanced') && (
                <div className="mb-6 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-center">
                    <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-bold mr-3">
                      AI
                    </div>
                    <div>
                      <h4 className="font-medium text-blue-900">AI Enhanced Analysis</h4>
                      <p className="text-sm text-blue-700">
                        This analysis has been enhanced with AI-powered insights and recommendations
                        {staticResults.parsed_results?.ai_metadata?.enhancement_timestamp && (
                          <span className="ml-2">
                            • Enhanced: {new Date(staticResults.parsed_results.ai_metadata.enhancement_timestamp).toLocaleString()}
                          </span>
                        )}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Summary Section */}
              <div className="mb-6">
                <h4 className="font-medium text-gray-900 mb-3">Summary</h4>
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="grid grid-cols-5 gap-4 text-center">
                    <div>
                      <div className="text-2xl font-bold text-gray-900">
                        {staticResults.parsed_results?.summary?.total || 0}
                      </div>
                      <div className="text-sm text-gray-600">Total</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-red-600">
                        {staticResults.parsed_results?.summary?.high || 0}
                      </div>
                      <div className="text-sm text-gray-600">High</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-orange-600">
                        {staticResults.parsed_results?.summary?.medium || 0}
                      </div>
                      <div className="text-sm text-gray-600">Medium</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-yellow-600">
                        {staticResults.parsed_results?.summary?.low || 0}
                      </div>
                      <div className="text-sm text-gray-600">Low</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-blue-600">
                        {staticResults.parsed_results?.summary?.informational || 0}
                      </div>
                      <div className="text-sm text-gray-600">Info</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* AI Recommendations Section - Show if AI results exist */}
              {staticResults.ai_results && (
                <div className="mb-6">
                  <h4 className="font-medium text-gray-900 mb-3">
                    AI Recommendations ({staticResults.ai_results.length})
                  </h4>
                  <div className="space-y-3 max-h-64 overflow-y-auto">
                    {staticResults.ai_results.map((recommendation, index) => (
                      <div key={index} className="border rounded-lg p-4 bg-blue-50 border-blue-200">
                        <div className="flex items-start">
                          <div className="w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold mr-3 mt-1">
                            AI
                          </div>
                          <div className="flex-1">
                            {typeof recommendation === 'string' ? (
                              <p className="text-sm text-blue-800">{recommendation}</p>
                            ) : (
                              <>
                                <h5 className="font-medium text-blue-900">
                                  {recommendation.title || `Recommendation ${index + 1}`}
                                </h5>
                                <p className="text-sm text-blue-800 mt-1">
                                  {recommendation.description || recommendation}
                                </p>
                                {recommendation.priority && (
                                  <span className={`inline-block px-2 py-1 text-xs font-medium rounded-full mt-2 ${
                                    recommendation.priority === 'high' ? 'bg-red-100 text-red-800' :
                                    recommendation.priority === 'medium' ? 'bg-orange-100 text-orange-800' :
                                    'bg-yellow-100 text-yellow-800'
                                  }`}>
                                    {recommendation.priority} priority
                                  </span>
                                )}
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Vulnerabilities Section */}
              <div className="mb-6">
                <h4 className="font-medium text-gray-900 mb-3">
                  {staticResults.display_mode === 'ai_enhanced' ? 'AI Enhanced ' : ''}
                  Vulnerabilities ({staticResults.parsed_results?.vulnerabilities?.length || 0})
                </h4>
                {staticResults.parsed_results?.vulnerabilities?.length > 0 ? (
                  <div className="space-y-3 max-h-64 overflow-y-auto">
                    {staticResults.parsed_results.vulnerabilities.map((vuln, index) => (
                      <div key={index} className={`border rounded-lg p-4 ${
                        staticResults.display_mode === 'ai_enhanced' 
                          ? 'bg-gradient-to-r from-gray-50 to-blue-50 border-blue-200' 
                          : 'bg-gray-50'
                      }`}>
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center">
                              {staticResults.display_mode === 'ai_enhanced' && (
                                <div className="w-4 h-4 bg-blue-600 text-white rounded-full flex items-center justify-center text-xs font-bold mr-2">
                                  AI
                                </div>
                              )}
                              <h5 className="font-medium text-gray-900">{vuln.title}</h5>
                            </div>
                            <p className="text-sm text-gray-600 mt-1">{vuln.description}</p>
                            
                            {/* AI-specific fields */}
                            {vuln.impact && (
                              <p className="text-sm text-orange-600 mt-2">
                                <strong>Impact:</strong> {vuln.impact}
                              </p>
                            )}
                            
                            {vuln.recommendation && (
                              <p className="text-sm text-blue-600 mt-2">
                                <strong>AI Recommendation:</strong> {vuln.recommendation}
                              </p>
                            )}

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
                  <p className="text-gray-500 text-center py-4">No vulnerabilities found</p>
                )}
              </div>

              {/* Raw Results Section - Only show for static results */}
              {!staticResults.display_mode || staticResults.display_mode !== 'ai_enhanced' ? (
                <details className="mb-4">
                  <summary className="cursor-pointer font-medium text-gray-900 mb-3">
                    Raw Slither Output (Click to expand)
                  </summary>
                  <div className="bg-gray-900 text-gray-100 rounded-lg overflow-hidden">
                    <div className="p-3 bg-gray-800 border-b border-gray-700 flex justify-between items-center">
                      <span className="text-sm font-medium">Raw JSON Output</span>
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(JSON.stringify(staticResults.slither_results, null, 2));
                          alert('Raw JSON copied to clipboard!');
                        }}
                        className="px-2 py-1 bg-gray-600 text-white text-xs rounded hover:bg-gray-500"
                      >
                        Copy JSON
                      </button>
                    </div>
                    <div className="p-4 overflow-x-auto max-h-96">
                      <pre className="text-sm text-left whitespace-pre-wrap">
                        {JSON.stringify(staticResults.slither_results, null, 2)}
                      </pre>
                    </div>
                  </div>
                </details>
              ) : (
                /* AI Results Raw Data */
                <details className="mb-4">
                  <summary className="cursor-pointer font-medium text-gray-900 mb-3">
                    AI Analysis Data (Click to expand)
                  </summary>
                  <div className="bg-blue-900 text-blue-100 rounded-lg overflow-hidden">
                    <div className="p-3 bg-blue-800 border-b border-blue-700 flex justify-between items-center">
                      <span className="text-sm font-medium">AI Enhanced Data</span>
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(JSON.stringify(staticResults.parsed_results, null, 2));
                          alert('AI data copied to clipboard!');
                        }}
                        className="px-2 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-500"
                      >
                        Copy Data
                      </button>
                    </div>
                    <div className="p-4 overflow-x-auto max-h-96">
                      <pre className="text-sm text-left whitespace-pre-wrap">
                        {JSON.stringify(staticResults.parsed_results, null, 2)}
                      </pre>
                    </div>
                  </div>
                </details>
              )}
            </div>

            <div className="border-t p-6">
              <div className="flex justify-between items-center">
                <div className="text-sm text-gray-600 text-left">
                  Analysis ID: {staticResults.analysis_id} • 
                  Status: {staticResults.status} • 
                  {staticResults.completed_at && 
                    `Completed: ${new Date(staticResults.completed_at).toLocaleString()}`
                  }
                  {staticResults.display_mode === 'ai_enhanced' && (
                    <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                      AI Enhanced
                    </span>
                  )}
                </div>
                <button
                  onClick={closeStaticModal}
                  className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProjectDetail;
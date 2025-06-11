class ProjectService {

  /* Projects APIs */
  
  static async getProjects(token) {
    console.log('Calling getProjects API with token:', token ? 'Present' : 'Missing');  

    const response = await fetch('/api/projects/', {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('API Error response:', errorText);
      throw new Error(`Failed to fetch projects: ${response.status} ${errorText}`);
    }

    return response.json();
  }

  static async getProjectDetail(projectId, token) {
    console.log('Calling getProjectDetail API for project:', projectId);

    const response = await fetch(`/api/projects/${projectId}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Project detail error:', errorText);
      throw new Error(`Failed to fetch project detail: ${response.status} ${errorText}`);
    }

    return response.json();
  }

  static async getProjectSource(projectId, filePath = null, token) {
    const url = filePath 
      ? `/api/projects/${projectId}/source?file_path=${encodeURIComponent(filePath)}`
      : `/api/projects/${projectId}/source`;
    
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      throw new Error('Failed to fetch project source');
    }

    return response.json();
  }

  /* Analysis APIs */

  static async getProjectAnalyses(projectId, token) {
    const response = await fetch(`/api/analysis/project/${projectId}/analyses`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      throw new Error('Failed to fetch analyses');
    }

    return response.json();
  }

  /* Normal User Auto Analysis */
  static async performAutoAnalysis(projectId, token) {
    
    const response = await fetch(`/api/analysis/analyze/${projectId}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.error('❌ Auto analysis error response:', errorData);
      throw new Error(errorData.detail || 'Foundry analysis failed');
    }

    const result = await response.json();
    return result;
  }

  static async getAnalysis(analysisId, token) {
    const response = await fetch(`/api/analysis/${analysisId}`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      throw new Error('Failed to fetch analysis');
    }

    return response.json();
  }

  /* Auditor Analysis APIs */

  // Enhanced Foundry Analysis APIs
  
  static async performFoundryAnalysis(projectId, options, token) {
    const response = await fetch(`/api/analysis/analyze/${projectId}/foundry`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(options)
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Foundry analysis failed');
    }

    return response.json();
  }

  static async getProjectStructure(analysisId, token) {
    const response = await fetch(`/api/analysis/${analysisId}/project-structure`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      throw new Error('Failed to fetch project structure');
    }

    return response.json();
  }

  static async performStaticAnalysis(projectId, options, token, projectType = 'single_file') {
    // console.log(`🔄 Starting ${projectType} analysis for project ${projectId}`);
    
    if (projectType === 'foundry_project') {
      return this.performFoundryAnalysis(projectId, options, token);
    } else {
      return this.performSingleFileAnalysis(projectId, options, token);
    }
  }

  static async performFoundryAnalysis(projectId, options, token) {
    // console.log('🔧 Using Foundry endpoint');
    
    const response = await fetch(`/api/analysis/analyze/${projectId}/foundry`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        // target_files: options.target_files || [],
        detectors: options.detectors || [],
        exclude_detectors: options.exclude_detectors || [],
        exclude_dependencies: options.exclude_dependencies !== false,
        exclude_informational: options.exclude_informational || false,
        exclude_low: options.exclude_low || false
      })
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Foundry analysis failed');
    }

    return response.json();
  }

  static async performSingleFileAnalysis(projectId, options, token) {
    // console.log('📄 Using single file endpoint');
    
    const response = await fetch(`/api/analysis/analyze/${projectId}/static`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        slither_options: options
      })
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Static analysis failed');
    }

    return response.json();
  }

  static async performAiEnhancement(analysisId, token) {
    const response = await fetch(`/api/analysis/analyze/${analysisId}/ai-enhance`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.error('AI enhancement error:', errorData);
      throw new Error(errorData.detail || errorData.message || 'AI enhancement failed');
    }

    return response.json();
  }

  static async generateReport(analysisId, format = 'html', token) {
    const response = await fetch(`/api/analysis/analyze/${analysisId}/generate-report`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ format_type: format })
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error('Report generation error:', errorData);
      throw new Error(errorData.detail || errorData.message || 'Report generation failed');
    }

    return response.json();
  }

  /* Helper APIs for Auditors */
  static async getAvailableDetectors(token) {
    const response = await fetch('/api/analysis/detectors', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      throw new Error('Failed to fetch detectors');
    }

    return response.json();
  }

  static async modifyResults(analysisId, modifiedData, token) {
    const response = await fetch(`/api/analysis/${analysisId}/modify-results`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(modifiedData)
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error('Modify results error:', errorData);
      throw new Error(errorData.detail || errorData.message || 'Failed to modify results');
    }

    return response.json();
  }

  /* Report APIs */
  static async getStaticResults(analysisId, token) {
    const response = await fetch(`/api/analysis/${analysisId}/static-results`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      throw new Error('Failed to fetch static results');
    }

    return response.json();
  }

  // Enhanced version with better error handling
  // static async getStaticResults(analysisId, token) {
  //   console.log('🔍 ProjectService.getStaticResults called:');
  //   console.log('  - analysisId:', analysisId);
  //   console.log('  - token present:', !!token);
  //   console.log('  - token preview:', token ? token.substring(0, 20) + '...' : 'None');
    
  //   const url = `/api/analysis/${analysisId}/static-results`;
  //   console.log('  - Full URL:', url);
    
  //   try {
  //     const response = await fetch(url, {
  //       method: 'GET',
  //       headers: {
  //         'Content-Type': 'application/json',
  //         'Authorization': `Bearer ${token}`
  //       }
  //     });

  //     console.log('📡 Response received:');
  //     console.log('  - Status:', response.status);
  //     console.log('  - Status Text:', response.statusText);
  //     console.log('  - Headers:', Object.fromEntries(response.headers.entries()));

  //     if (!response.ok) {
  //       // Enhanced error handling
  //       let errorMessage;
  //       try {
  //         const errorData = await response.json();
  //         console.error('❌ Error response data:', errorData);
  //         errorMessage = errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`;
  //       } catch (parseError) {
  //         console.error('❌ Could not parse error response:', parseError);
  //         const errorText = await response.text();
  //         console.error('❌ Raw error response:', errorText);
  //         errorMessage = `HTTP ${response.status}: ${response.statusText}`;
  //       }
        
  //       throw new Error(`Failed to fetch static results: ${errorMessage}`);
  //     }

  //     const data = await response.json();
  //     console.log('✅ Static results data received:', data);
  //     return data;
      
  //   } catch (fetchError) {
  //     console.error('❌ Fetch error:', fetchError);
  //     throw fetchError;
  //   }
  // }

  static async getAnalysisReport(analysisId, token) {
    const response = await fetch(`/api/analysis/${analysisId}/report`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Unknown error');
      console.error('Report fetch error:', errorText);
      
      if (response.status === 404) {
        throw new Error('Report not found. Please generate the report first.');
      } else if (response.status === 403) {
        throw new Error('Access denied. You don\'t have permission to view this report.');
      } else if (response.status === 400) {
        throw new Error('Analysis not completed yet. Please wait for the analysis to finish.');
      } else {
        throw new Error(`Failed to fetch report: ${response.status} ${response.statusText}`);
      }
    }

    return response.text();
  }

  static async downloadReport(analysisId, projectName, token) {
    try {
      const htmlContent = await this.getAnalysisReport(analysisId, token);
      
      if (!htmlContent || htmlContent.trim().length === 0) {
        throw new Error('Report content is empty');
      }

      const blob = new Blob([htmlContent], { type: 'text/html; charset=utf-8' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `analysis-report-${projectName}-${new Date().toISOString().split('T')[0]}.html`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

    } catch (error) {
      throw new Error('Download failed: ' + error.message);
    }
  }

  static async viewReport(analysisId, token) {
    try {
      const htmlContent = await this.getAnalysisReport(analysisId, token);

      if (!htmlContent || htmlContent.trim().length === 0) {
        throw new Error('Report content is empty');
      }
      
      const newWindow = window.open('', '_blank');
      if (!newWindow) {
        throw new Error('Popup blocked. Please allow popups for this site.');
      }
      
      newWindow.document.write(htmlContent);
      newWindow.document.close();

    } catch (error) {
      throw new Error('Failed to view report: ' + error.message);
    }
  }

  static async getAiResults(analysisId, token) {
    // console.log('🤖 Fetching AI results for analysis:', analysisId);
    
    const response = await fetch(`/api/analysis/${analysisId}/ai-results`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error('AI results fetch error:', errorData);
      throw new Error(errorData.detail || errorData.message || 'Failed to fetch AI results');
    }

    const result = await response.json();
    // console.log('✅ AI results received:', result);
    return result;
  }


}

export default ProjectService

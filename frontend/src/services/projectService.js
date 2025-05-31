class ProjectService {
  static async getProjects(token) {
    const response = await fetch('/api/upload/projects', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      throw new Error('Failed to fetch projects');
    }

    return response.json();
  }

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

  static async startAnalysis(projectId, token) {
    const response = await fetch(`/api/analysis/analyze/${projectId}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Analysis failed');
    }

    return response.json();
  }

  static async getAnalysis(analysisId, token) {
    const response = await fetch(`/api/analysis/analysis/${analysisId}`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      throw new Error('Failed to fetch analysis');
    }

    return response.json();
  }

  static async getAnalysisReport(analysisId, token) {
    const response = await fetch(`/api/analysis/analysis/${analysisId}/report`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      throw new Error('Failed to fetch report');
    }

    return response.text();
  }

  static async downloadReport(analysisId, projectName, token) {
    try {
      const htmlContent = await this.getAnalysisReport(analysisId, token);
      const blob = new Blob([htmlContent], { type: 'text/html' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `analysis-report-${projectName}.html`;
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
      const newWindow = window.open();
      newWindow.document.write(htmlContent);
    } catch (error) {
      throw new Error('Failed to view report: ' + error.message);
    }
  }
}

export default ProjectService;
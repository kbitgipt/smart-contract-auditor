import React, { useState } from 'react';
import { Settings, User, Shield } from 'lucide-react';
import useAuthStore from '../../stores/authStore';

const ModeSwitcher = () => {
  const { user, updateUserMode } = useAuthStore();
  const [isUpdating, setIsUpdating] = useState(false);

  const handleModeChange = async (newMode) => {
    if (isUpdating || user.user_mode === newMode) return;
    
    setIsUpdating(true);
    try {
      await updateUserMode(newMode);
    } catch (error) {
      console.error('Failed to update mode:', error);
      alert('Failed to update mode. Please try again.');
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <div className="flex items-center gap-2 p-2 bg-white rounded-lg border">
      <Settings className="w-4 h-4 text-gray-500" />
      <span className="text-sm font-medium text-gray-700">Mode:</span>
      
      <div className="flex gap-1">
        <button
          onClick={() => handleModeChange('normal')}
          disabled={isUpdating}
          className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
            user.user_mode === 'normal'
              ? 'bg-blue-100 text-blue-700 border border-blue-200'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          } ${isUpdating ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          <User className="w-3 h-3 inline mr-1" />
          Normal
        </button>
        
        <button
          onClick={() => handleModeChange('auditor')}
          disabled={isUpdating}
          className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
            user.user_mode === 'auditor'
              ? 'bg-purple-100 text-purple-700 border border-purple-200'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          } ${isUpdating ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          <Shield className="w-3 h-3 inline mr-1" />
          Auditor
        </button>
      </div>
      
      {isUpdating && (
        <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      )}
    </div>
  );
};

export default ModeSwitcher;
import React, { useState } from 'react';
import axios from 'axios';
import { useAuth } from './contexts/AuthContext';
import './styles.css';

const ImageUpload = ({ onImageUploaded }) => {
  const { currentUser } = useAuth();
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    setFile(selectedFile);
    setMessage('');
    setError(null);
    setUploadProgress(0);
    
    if (selectedFile) {
      const reader = new FileReader();
      reader.onload = () => {
        setPreview(reader.result);
      };
      reader.readAsDataURL(selectedFile);
    } else {
      setPreview(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file first');
      return;
    }

    setLoading(true);
    setError(null);
    setUploadProgress(0);
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      console.log('Sending request to upload endpoint...');
      const response = await axios.post('http://localhost:5000/upload', formData, {
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percentCompleted);
        }
      });
      
      console.log('Response received:', response.data);
      setMessage(response.data.message);
      
      if (onImageUploaded && response.data) {
        onImageUploaded(response.data);
      }

      const userProfileResponse = await axios.get(`http://localhost:5000/user/profile?user_id=${currentUser.user_id}`);
    } catch (error) {
      console.error('Error uploading file:', error);
      setError(
        error.response
          ? `Error: ${error.response.status} - ${error.response.data.error || 'Unknown error'}`
          : 'Network error. Is the backend server running?'
      );
    } finally {
      setLoading(false);
      setUploadProgress(0);
    }
  };

  return (
    <div className="upload-container">
      <div className="mb-3">
        <input 
          type="file" 
          className="form-control" 
          onChange={handleFileChange} 
          accept="image/*" 
          disabled={loading}
        />
      </div>
      
      {preview && (
        <div className="mb-3 text-center">
          <div className="image-preview-container">
            <img 
              src={preview} 
              alt="Preview" 
              className="img-preview" 
              style={{ maxHeight: '250px' }}
            />
            {loading && (
              <div className="upload-progress">
                <div 
                  className="progress-bar" 
                  role="progressbar" 
                  style={{ width: `${uploadProgress}%` }}
                  aria-valuenow={uploadProgress} 
                  aria-valuemin="0" 
                  aria-valuemax="100"
                >
                  {uploadProgress}%
                </div>
              </div>
            )}
          </div>
        </div>
      )}
      
      <button 
        className="btn btn-primary w-100" 
        onClick={handleUpload} 
        disabled={loading || !file}
      >
        {loading ? (
          <>
            <i className="bi bi-arrow-repeat spinner me-2"></i>
            Uploading... {uploadProgress}%
          </>
        ) : (
          <>
            <i className="bi bi-cloud-arrow-up me-2"></i>
            Upload Image
          </>
        )}
      </button>
      
      {message && !error && (
        <div className="mt-3 alert alert-success">
          <i className="bi bi-check-circle-fill me-2"></i>
          {message}
        </div>
      )}
      
      {error && (
        <div className="mt-3 alert alert-danger">
          <i className="bi bi-exclamation-triangle-fill me-2"></i>
          {error}
        </div>
      )}
    </div>
  );
};

export default ImageUpload;
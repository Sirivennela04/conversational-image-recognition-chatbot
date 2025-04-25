import React, { useState, useEffect } from 'react';
import './App.css';
import ImageUpload from './ImageUpload';
import ChatInterface from './ChatInterface';
import 'bootstrap/dist/css/bootstrap.min.css';
import axios from 'axios';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import AuthModal from './components/AuthModal';
import UserProfile from './components/UserProfile';
import ChatSidebar from './components/ChatSidebar';

function AppContent() {
  const [serverStatus, setServerStatus] = useState({ loading: true, error: null, data: null });
  const [currentImage, setCurrentImage] = useState(null);
  const [chatHistory, setChatHistory] = useState([]);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const { currentUser } = useAuth();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const checkServerStatus = async () => {
      try {
        const response = await axios.get('http://localhost:5000/status');
        setServerStatus({ 
          loading: false, 
          data: response.data, 
          error: null 
        });
      } catch (error) {
        setServerStatus({ 
          loading: false, 
          data: null, 
          error: 'Cannot connect to server. Please ensure the backend is running.' 
        });
      }
    };

    checkServerStatus();
  }, []);

  const handleImageUploaded = (imageData) => {
    console.log('Image uploaded:', imageData);
    setCurrentImage(imageData);
    setChatHistory([]);
    
    if (imageData && imageData.image_id) {
      loadChatHistory(imageData.image_id);
    }
  };

  const loadChatHistory = async (imageId) => {
    try {
      const response = await axios.get(`http://localhost:5000/chat-history?image_id=${imageId}`);
      if (response.data && Array.isArray(response.data.chat_history)) {
        setChatHistory(response.data.chat_history);
      }
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  };

  const handleSelectImage = async (data) => {
    try {
      setLoading(true);
      setCurrentImage(data.image);
      setChatHistory(data.chatHistory);
    } catch (err) {
      console.error('Error loading image:', err);
    } finally {
      setLoading(false);
    }
  };

  const renderStatusAlert = () => {
    if (serverStatus.loading) {
      return (
        <div className="alert alert-info">
          <i className="bi bi-hourglass-split me-2"></i>
          Connecting to server...
        </div>
      );
    }
    
    if (serverStatus.error) {
      return (
        <div className="alert alert-danger">
          <i className="bi bi-exclamation-triangle-fill me-2"></i>
          {serverStatus.error}
        </div>
      );
    }
    
    if (serverStatus.data && serverStatus.data.database && serverStatus.data.database.status !== "Connected") {
      return (
        <div className="alert alert-warning">
          <i className="bi bi-database-x me-2"></i>
          Database connection issue: {serverStatus.data.database.error || 'Unknown error'}
        </div>
      );
    }
    
    return (
      <div className="alert alert-success">
        <i className="bi bi-check-circle-fill me-2"></i>
        Server and database connected successfully
      </div>
    );
  };

  const hasAnalysisData = () => {
    return currentImage && 
           currentImage.analysis && 
           currentImage.analysis.labels && 
           Array.isArray(currentImage.analysis.labels);
  };

  const openAuthModal = () => {
    setShowAuthModal(true);
  };

  const closeAuthModal = () => {
    setShowAuthModal(false);
  };

  return (
    <div className="App">
      <nav className="navbar navbar-expand-lg navbar-dark bg-dark">
        <div className="container">
          <a className="navbar-brand" href="#">
            <i className="bi bi-camera"></i> Image Classifier Chatbot
          </a>
          <div className="ms-auto d-flex align-items-center">
            {currentUser ? (
              <div className="dropdown">
                <button className="btn btn-outline-light dropdown-toggle" type="button" id="userDropdown" data-bs-toggle="dropdown" aria-expanded="false">
                  <i className="bi bi-person-circle me-1"></i> {currentUser.username}
                </button>
                <ul className="dropdown-menu dropdown-menu-end" aria-labelledby="userDropdown">
                  <li>
                    <div className="dropdown-item-text">
                      <UserProfile />
                    </div>
                  </li>
                </ul>
              </div>
            ) : (
              <button className="btn btn-outline-light" onClick={openAuthModal}>
                <i className="bi bi-box-arrow-in-right me-1"></i> Login / Register
              </button>
            )}
          </div>
        </div>
      </nav>
      
      <div className="main-content-wrapper">
        {/* Chat History Sidebar */}
        <ChatSidebar onSelectImage={handleSelectImage} />
        
        {/* Main Content Area */}
        <div className="main-content">
          <div className="container py-4">
            <div className="row justify-content-center">
              <div className="col-md-10">
                <div className="mb-4">
                  {renderStatusAlert()}
                </div>
                
                <div className="text-center mb-4">
                  <h1 className="display-5">Image Recognition Chatbot</h1>
                  <p className="lead text-muted">
                    Upload an image and ask questions about what's in it
                  </p>
                </div>
                
                {loading ? (
                  <div className="text-center py-5">
                    <div className="spinner-border text-primary" role="status">
                      <span className="visually-hidden">Loading...</span>
                    </div>
                    <p className="mt-3">Loading selected image...</p>
                  </div>
                ) : (
                  <>
                    <div className="row">
                      <div className="col-md-6 mb-4">
                        <div className="card">
                          <div className="card-header">
                            <h5 className="mb-0">
                              <i className="bi bi-cloud-upload me-2"></i>
                              Upload Image
                            </h5>
                          </div>
                          <div className="card-body">
                            <ImageUpload onImageUploaded={handleImageUploaded} />
                          </div>
                        </div>
                      </div>
                      
                      <div className="col-md-6 mb-4">
                        <div className="card">
                          <div className="card-header">
                            <h5 className="mb-0">
                              <i className="bi bi-chat-dots me-2"></i>
                              Chat with AI
                            </h5>
                          </div>
                          <div className="card-body">
                            {currentImage ? (
                              <ChatInterface 
                                imageId={currentImage.image_id} 
                                initialHistory={chatHistory}
                                userId={currentUser?.user_id || 'anonymous'}
                              />
                            ) : (
                              <div className="text-center py-5 text-muted">
                                <i className="bi bi-image fs-1 d-block mb-3"></i>
                                <p>Upload an image or select one from history to start chatting</p>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    {currentImage && hasAnalysisData() && (
                      <div className="card mb-4">
                        <div className="card-header">
                          <h5 className="mb-0">
                            <i className="bi bi-tags me-2"></i>
                            Detected Objects
                          </h5>
                        </div>
                        <div className="card-body">
                          <div className="row">
                            <div className="col-md-6">
                              <h6>Image Information</h6>
                              <p>
                                <strong>Title:</strong> {currentImage.title || currentImage.filename || "Untitled"}
                              </p>
                              <p>
                                <strong>Description:</strong> {currentImage.description || "No description provided"}
                              </p>
                            </div>
                            <div className="col-md-6">
                              <h6>Labels</h6>
                              <div className="d-flex flex-wrap gap-2">
                                {currentImage.analysis.labels.map((label, index) => (
                                  <span key={index} className="badge bg-primary">
                                    {label.label} ({Math.round(label.confidence * 100)}%)
                                  </span>
                                ))}
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <AuthModal isOpen={showAuthModal} onClose={closeAuthModal} />
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
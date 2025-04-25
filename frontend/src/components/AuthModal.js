import React, { useState } from 'react';
import Login from './Login';
import Register from './Register';
import '../styles.css';

const AuthModal = ({ isOpen, onClose }) => {
  const [showLogin, setShowLogin] = useState(true);
  
  if (!isOpen) return null;
  
  const handleShowRegister = () => {
    setShowLogin(false);
  };
  
  const handleShowLogin = () => {
    setShowLogin(true);
  };
  
  return (
    <div className="modal-overlay">
      <div className="modal-container">
        <button className="modal-close-btn" onClick={onClose}>
          <i className="bi bi-x-lg"></i>
        </button>
        
        <div className="modal-content">
          {showLogin ? (
            <Login 
              onClose={onClose} 
              showRegister={handleShowRegister} 
            />
          ) : (
            <Register 
              onClose={onClose} 
              showLogin={handleShowLogin} 
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default AuthModal; 
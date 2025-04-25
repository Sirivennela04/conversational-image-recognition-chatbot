import React, { createContext, useState, useEffect, useContext } from 'react';
import axios from 'axios';

// Create a context
const AuthContext = createContext();

// Create a provider component
export const AuthProvider = ({ children }) => {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check for saved user data on initial load
  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
      try {
        setCurrentUser(JSON.parse(savedUser));
      } catch (err) {
        console.error('Failed to parse user data:', err);
        localStorage.removeItem('user');
      }
    }
    setLoading(false);
  }, []);

  // Register function
  const register = async (userData) => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post('http://localhost:5000/register', userData);
      const user = response.data;
      setCurrentUser({
        user_id: user.user_id,
        username: userData.username,
        email: userData.email
      });
      localStorage.setItem('user', JSON.stringify({
        user_id: user.user_id,
        username: userData.username,
        email: userData.email
      }));
      return user;
    } catch (err) {
      setError(err.response?.data?.error || 'Registration failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Login function
  const login = async (credentials) => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post('http://localhost:5000/login', credentials);
      const { user } = response.data;
      setCurrentUser(user);
      localStorage.setItem('user', JSON.stringify(user));
      return user;
    } catch (err) {
      setError(err.response?.data?.error || 'Login failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Logout function
  const logout = () => {
    setCurrentUser(null);
    localStorage.removeItem('user');
  };

  const updateUserProfile = async (userId) => {
    try {
      const response = await axios.get(`http://localhost:5000/user/profile?user_id=${userId}`);
      setCurrentUser(prev => ({
        ...prev,
        ...response.data // Assuming response.data contains the updated user info
      }));
    } catch (err) {
      console.error('Error updating user profile:', err);
    }
  };

  // Create context value
  const value = {
    currentUser,
    loading,
    error,
    register,
    login,
    logout,
    updateUserProfile
  };

  // Return provider with value
  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Custom hook to use the auth context
export const useAuth = () => {
  return useContext(AuthContext);
}; 
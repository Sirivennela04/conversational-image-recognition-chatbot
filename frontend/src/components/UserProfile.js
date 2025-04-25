import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';

const UserProfile = () => {
  const { currentUser, logout } = useAuth();
  const [profileData, setProfileData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newUsername, setNewUsername] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [updateSuccess, setUpdateSuccess] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    const fetchUserProfile = async () => {
      if (!currentUser) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const response = await axios.get(`http://localhost:5000/user/profile?user_id=${currentUser.user_id}`);
        setProfileData(response.data);
        setNewUsername(response.data.username || '');
        setNewEmail(response.data.email || '');
        setError(null);
      } catch (err) {
        console.error('Error fetching user profile:', err);
        setError('Failed to load user profile');
      } finally {
        setLoading(false);
      }
    };

    fetchUserProfile();
  }, [currentUser]);

  const handleUpdate = async (e) => {
    e.stopPropagation(); 
    try {
      if (newPassword && newPassword !== confirmPassword) {
        setError('Passwords do not match');
        return;
      }

      const updateData = {
        user_id: currentUser.user_id,
        username: newUsername || undefined,
        email: newEmail || undefined,
        password: newPassword || undefined
      };

      const response = await axios.put('http://localhost:5000/user/update', updateData);
      
      if (response.data.message) {
        setUpdateSuccess(true);
        setError(null);
        setNewPassword('');
        setConfirmPassword('');
        const profileResponse = await axios.get(`http://localhost:5000/user/profile?user_id=${currentUser.user_id}`);
        setProfileData(profileResponse.data);
        setIsEditing(false);
      }
    } catch (err) {
      console.error('Error updating profile:', err);
      setError(err.response?.data?.error || 'Failed to update profile');
      setUpdateSuccess(false);
    }
  };

  const handleDelete = async (e) => {
    e.stopPropagation();
    try {
      const response = await axios.delete('http://localhost:5000/user/delete', {
        data: { user_id: currentUser.user_id }
      });
      
      if (response.data.message) {
        logout();
      }
    } catch (err) {
      console.error('Error deleting account:', err);
      setError(err.response?.data?.error || 'Failed to delete account');
      setShowDeleteConfirm(false);
    }
  };

  const handleLogout = (e) => {
    e.stopPropagation();
    logout();
  };

  const handleEditClick = (e) => {
    e.stopPropagation();
    setIsEditing(true);
  };

  const handleDeleteClick = (e) => {
    e.stopPropagation();
    setShowDeleteConfirm(true);
  };

  const handleCancelEdit = (e) => {
    e.stopPropagation();
    setError(null);
    setUpdateSuccess(false);
  };

  const handleCancelDelete = (e) => {
    e.stopPropagation();
    setShowDeleteConfirm(false);
  };

  if (!currentUser) {
    return null;
  }

  return (
    <div className="user-profile-container" onClick={(e) => e.stopPropagation()}>
      <div className="card">
        <div className="card-body">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h5 className="card-title mb-0">User Profile</h5>
            <button 
              className="btn btn-outline-danger btn-sm"
              onClick={handleLogout}
            >
              <i className="bi bi-box-arrow-right me-1"></i>
              Logout
            </button>
          </div>
          
          {loading ? (
            <div className="text-center">
              <div className="spinner-border text-primary" role="status">
                <span className="visually-hidden">Loading...</span>
              </div>
            </div>
          ) : error ? (
            <div className="alert alert-danger">{error}</div>
          ) : profileData ? (
            <div>
              {!isEditing ? (
                <div>
                  <p className="mb-1"><strong>Username:</strong> {profileData.username}</p>
                  <p className="mb-1"><strong>Email:</strong> {profileData.email}</p>
                  {profileData.chat_count !== undefined && (
                    <p className="mb-1"><strong>Chat Interactions:</strong> {profileData.chat_count}</p>
                  )}
                  {profileData.last_login && (
                    <p className="mb-1"><strong>Last Login:</strong> {new Date(profileData.last_login).toLocaleString()}</p>
                  )}
                  <div className="d-flex gap-2 mt-3">
                    <button 
                      className="btn btn-primary"
                      onClick={handleEditClick}
                    >
                      <i className="bi bi-pencil-square me-1"></i>
                      Edit Profile
                    </button>
                    <button 
                      className="btn btn-danger"
                      onClick={handleDeleteClick}
                    >
                      <i className="bi bi-trash me-1"></i>
                      Delete Account
                    </button>
                  </div>
                </div>
              ) : (
                <div className="mt-4">
                  <h6>Update Profile</h6>
                  <div className="mb-3">
                    <label className="form-label">Username</label>
                    <input
                      type="text"
                      className="form-control"
                      value={newUsername}
                      onChange={(e) => setNewUsername(e.target.value)}
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label">Email</label>
                    <input
                      type="email"
                      className="form-control"
                      value={newEmail}
                      onChange={(e) => setNewEmail(e.target.value)}
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label">New Password (leave blank to keep current)</label>
                    <input
                      type="password"
                      className="form-control"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label">Confirm New Password</label>
                    <input
                      type="password"
                      className="form-control"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                    />
                  </div>
                  <div className="d-flex gap-2">
                    <button 
                      className="btn btn-primary"
                      onClick={handleUpdate}
                    >
                      Update Profile
                    </button>
                    <button 
                      className="btn btn-secondary"
                      onClick={handleCancelEdit}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p>No profile data available</p>
          )}

          {updateSuccess && (
            <div className="alert alert-success mt-3">
              Profile updated successfully!
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="modal-overlay" onClick={(e) => e.stopPropagation()}>
          <div className="modal-container">
            <div className="modal-content">
              <h5>Confirm Account Deletion</h5>
              <p className="text-danger">
                <i className="bi bi-exclamation-triangle-fill me-2"></i>
                Warning: This action cannot be undone. All your data will be permanently deleted.
              </p>
              <div className="d-flex gap-2 mt-3">
                <button 
                  className="btn btn-danger"
                  onClick={handleDelete}
                >
                  Yes, Delete My Account
                </button>
                <button 
                  className="btn btn-secondary"
                  onClick={handleCancelDelete}
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserProfile; 
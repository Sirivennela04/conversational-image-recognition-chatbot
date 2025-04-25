import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';

const ChatSidebar = ({ onSelectImage }) => {
  const { currentUser } = useAuth();
  const [chatHistory, setChatHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedItem, setExpandedItem] = useState(null);
  const [selectedImage, setSelectedImage] = useState(null);

  useEffect(() => {
    if (currentUser) {
      loadUserChatHistory();
    } else {
      setChatHistory([]);
    }
  }, [currentUser]);
  

  const loadUserChatHistory = async () => {
    if (!currentUser) return;

    try {
      setLoading(true);
      setError(null);
      
      const response = await axios.get(`http://localhost:5000/chat-history?user_id=${currentUser.user_id}`);
      
      if (response.data && Array.isArray(response.data.chat_history)) {
        const groupedHistory = processAndGroupChatHistory(response.data.chat_history);
        setChatHistory(groupedHistory);
      }
    } catch (err) {
      console.error('Error loading user chat history:', err);
      setError('Failed to load chat history');
    } finally {
      setLoading(false);
    }
  };

  const processAndGroupChatHistory = (history) => {
    const imageGroups = {};
    
    history.forEach(chat => {
      if (!chat.image_id) return;
      
      if (!imageGroups[chat.image_id]) {
        imageGroups[chat.image_id] = {
          image_id: chat.image_id,
          last_chat_time: chat.timestamp,
          chats: []
        };
      }
      
      if (chat.role === 'user') {
        const botResponse = history.find(msg => 
          msg.role === 'bot' && 
          msg.timestamp > chat.timestamp && 
          (!msg.image_id || msg.image_id === chat.image_id)
        );
        
        const contextTitle = chat.content.split(' ').slice(0, 5).join(' ') + '...';
        
        imageGroups[chat.image_id].chats.push({
          context_title: contextTitle,
          user_message: chat.content,
          bot_response: botResponse ? botResponse.content : 'No response',
          timestamp: chat.timestamp
        });
        
        if (new Date(chat.timestamp) > new Date(imageGroups[chat.image_id].last_chat_time)) {
          imageGroups[chat.image_id].last_chat_time = chat.timestamp;
        }
      }
    });
    
    return Object.values(imageGroups)
      .sort((a, b) => new Date(b.last_chat_time) - new Date(a.last_chat_time));
  };

  const handleExpandItem = (index) => {
    setExpandedItem(expandedItem === index ? null : index);
  };

  const handleSelectImage = async (imageId) => {
    try {
        setLoading(true);
        setError(null);
        
        console.log('Fetching image details for ID:', imageId);
        const imageResponse = await axios.get(`http://localhost:5000/images/${imageId}?user_id=${currentUser.user_id}`);
        
        console.log('Image response:', imageResponse.data);
        
        console.log('Fetching chat history for image ID:', imageId, 'and user ID:', currentUser.user_id);
        const chatResponse = await axios.get(`http://localhost:5000/chat-history?image_id=${imageId}&user_id=${currentUser.user_id}`);
        
        console.log('Chat response:', chatResponse.data);
        
        if (imageResponse.data && chatResponse.data) {
            onSelectImage({
                image: imageResponse.data,
                chatHistory: chatResponse.data.chat_history || []
            });
            
            setSelectedImage(imageId);
        }
    } catch (err) {
        console.error('Error loading image and chat history:', err);
        setError(err.response?.data?.error || 'Failed to load image and chat history');
    } finally {
        setLoading(false);
    }
  };

  const handleDeleteChat = async (imageId) => {
    if (!currentUser) return;
    
    try {
      setLoading(true);
      setError(null);
      
      if (!window.confirm('Are you sure you want to delete this chat history? This action cannot be undone.')) {
        return;
      }
      
      const response = await axios.delete(`http://localhost:5000/chat-history/${imageId}?user_id=${currentUser.user_id}`);
      
      if (response.data && response.data.message) {
        setChatHistory(prev => prev.filter(item => item.image_id !== imageId));
        
        if (selectedImage === imageId) {
          setSelectedImage(null);
        }
      }
    } catch (err) {
      console.error('Error deleting chat history:', err);
      setError('Failed to delete chat history: ' + (err.response?.data?.error || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  };

  if (!currentUser) {
    return (
      <div className="chat-sidebar">
        <div className="text-center p-3">
          <p className="text-muted">
            <i className="bi bi-person-lock me-2"></i>
            Please log in to view chat history
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-sidebar">
      <h5 className="sidebar-header px-3 py-2">
        <i className="bi bi-clock-history me-2"></i>
        Your Chat History
      </h5>

      {loading ? (
        <div className="text-center p-3">
          <div className="spinner-border spinner-border-sm text-primary" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
          <p className="mt-2 mb-0 text-muted">Loading chat history...</p>
        </div>
      ) : error ? (
        <div className="alert alert-danger m-2 p-2">
          <small>{error}</small>
        </div>
      ) : chatHistory.length === 0 ? (
        <div className="text-center p-3">
          <p className="text-muted">
            <i className="bi bi-chat-square me-2"></i>
            No chat history found
          </p>
        </div>
      ) : (
        <div className="history-list">
          {chatHistory.map((item, index) => (
            <div 
              key={item.image_id} 
              className={`history-item ${selectedImage === item.image_id ? 'selected' : ''}`}
            >
              <div 
                className="history-item-header" 
                onClick={() => handleExpandItem(index)}
              >
                <div className="d-flex align-items-center justify-content-between w-100">
                  <div className="history-context">
                    <i className="bi bi-chat-dots me-2"></i>
                    {item.chats[0]?.context_title || 'Chat Conversation'}
                  </div>
                  <div className="history-actions">
                    <button 
                      className="btn btn-sm btn-outline-danger me-2"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteChat(item.image_id);
                      }}
                    >
                      <i className="bi bi-trash"></i>
                    </button>
                    <i className={`bi ${expandedItem === index ? 'bi-chevron-up' : 'bi-chevron-down'}`}></i>
                  </div>
                </div>
              </div>
              
              {expandedItem === index && (
                <div className="history-item-details">
                  <button 
                    className="btn btn-sm btn-outline-primary mb-2"
                    onClick={() => handleSelectImage(item.image_id)}
                  >
                    <i className="bi bi-arrow-up-right-square me-1"></i>
                    View Full Chat
                  </button>
                  
                  {item.chats.slice(0, 3).map((chat, chatIndex) => (
                    <div key={chatIndex} className="history-chat-item">
                      <div className="history-chat-query">
                        <strong>You:</strong> {chat.user_message}
                      </div>
                      <div className="history-chat-response">
                        <strong>AI:</strong> {chat.bot_response.length > 100 
                          ? chat.bot_response.substring(0, 100) + '...' 
                          : chat.bot_response}
                      </div>
                    </div>
                  ))}
                  
                  {item.chats.length > 3 && (
                    <div className="text-center mt-2">
                      <small className="text-muted">
                        + {item.chats.length - 3} more conversations
                      </small>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ChatSidebar;
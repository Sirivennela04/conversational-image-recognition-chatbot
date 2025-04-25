import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './styles.css';

const ChatInterface = ({ imageId, initialHistory = [], userId = 'anonymous' }) => {
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const messagesEndRef = useRef(null);
  
  useEffect(() => {
    const loadHistory = async () => {
      setLoading(true);
      setError(null);
      console.log('Loading chat history with:', { imageId, userId, initialHistory });
      
      try {
        if (initialHistory && initialHistory.length > 0) {
          console.log('Using provided initial history:', initialHistory);
          setChatHistory(initialHistory);
        } else if (imageId) {
          console.log('Fetching chat history from server for image:', imageId);
          await loadChatHistory();
        } else {
          console.log('No imageId provided, cannot load chat history');
          setError('No image selected');
        }
      } catch (err) {
        console.error('Error loading chat history:', err);
        setError('Failed to load chat history: ' + (err.message || 'Unknown error'));
      } finally {
        setLoading(false);
      }
    };

    loadHistory();
  }, [imageId, initialHistory, userId]);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatHistory]);

  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (err) {
      return '';
    }
  };

  const loadChatHistory = async () => {
    if (!imageId) {
      console.log('No imageId provided to loadChatHistory');
      return;
    }
    
    try {
      console.log('Fetching chat history from:', `http://localhost:5000/chat-history?image_id=${imageId}&user_id=${userId}`);
      const response = await axios.get(`http://localhost:5000/chat-history?image_id=${imageId}&user_id=${userId}`);
      console.log('Chat history response:', response.data);
      
      if (response.data && response.data.chat_history) {
        const transformedHistory = response.data.chat_history.map(chat => ({
          role: chat.role,
          content: chat.content,
          id: chat.id || chat._id,
          timestamp: chat.timestamp,
          image_id: chat.image_id || imageId,
          image_title: chat.image_title || '',
          image_url: chat.image_url || ''
        }));
        
        console.log('Transformed chat history:', transformedHistory);
        setChatHistory(transformedHistory);
      } else {
        console.log('No chat history found in response');
        setChatHistory([]);
      }
    } catch (err) {
      console.error('Error loading chat history:', err);
      setError('Failed to load chat history: ' + (err.message || 'Unknown error'));
      setChatHistory([]);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    
    if (!message.trim() || !imageId) {
      console.log('Cannot send message:', { message: message.trim(), imageId });
      return;
    }
    
    try {
      setSending(true);
      setError(null);
      
      const userMessageObj = {
        role: 'user',
        content: message,
        id: 'temp-' + Date.now(),
        pending: true,
        timestamp: new Date().toISOString()
      };
      
      setChatHistory(prev => [...prev, userMessageObj]);
      
      console.log('Sending message to server:', { message, imageId, userId });
      const response = await axios.post('http://localhost:5000/chat', {
        message: message,
        image_id: imageId,
        user_id: userId
      });
      
      console.log('Server response:', response.data);
      
      setChatHistory(prev => [
        ...prev.filter(msg => msg.id !== userMessageObj.id),
        {
          role: 'user',
          content: message,
          id: 'user-' + Date.now(),
          timestamp: new Date().toISOString()
        },
        {
          role: 'bot',
          content: response.data.response,
          id: 'bot-' + Date.now(),
          timestamp: new Date().toISOString()
        }
      ]);
      
      setMessage('');
      
    } catch (err) {
      console.error('Error sending message:', err);
      setError(err.response?.data?.error || 'Failed to send message');
      
      setChatHistory(prev => prev.filter(msg => !msg.pending));
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="chat-interface">
      <div className="chat-messages">
        {loading ? (
          <div className="text-center py-4">
            <div className="spinner-border text-primary" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
            <p className="mt-2">Loading chat history...</p>
          </div>
        ) : error ? (
          <div className="text-center py-4 text-danger">
            <p>{error}</p>
            <button 
              className="btn btn-sm btn-outline-primary mt-2"
              onClick={() => loadChatHistory()}
            >
              Retry
            </button>
          </div>
        ) : chatHistory.length === 0 ? (
          <div className="text-center py-4 text-muted">
            <p>No messages yet. Start a conversation!</p>
          </div>
        ) : (
          chatHistory.map((chat, index) => (
            <div 
              key={chat.id || index} 
              className={`message ${chat.role === 'user' ? 'user-message' : 'bot-message'} ${chat.pending ? 'pending' : ''}`}
            >
              <div className="message-content">
                {chat.content}
                {chat.pending && <div className="spinner-grow spinner-grow-sm ms-2" role="status" />}
              </div>
              <div className="message-time">
                {formatTime(chat.timestamp)}
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>
      
      {error && (
        <div className="alert alert-danger mt-3">
          {error}
          <button 
            type="button" 
            className="btn-close float-end" 
            onClick={() => setError(null)}
            aria-label="Close"
          />
        </div>
      )}
      
      <form onSubmit={handleSendMessage} className="message-form mt-3">
        <div className="input-group">
          <input
            type="text"
            className="form-control"
            placeholder="Ask something about this image..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            disabled={sending || loading || !imageId}
          />
          <button 
            type="submit" 
            className="btn btn-primary"
            disabled={sending || loading || !message.trim() || !imageId}
          >
            {sending ? (
              <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
            ) : (
              <i className="bi bi-send"></i>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatInterface;
// Chatbot functionality
let chatbotSessionId = localStorage.getItem('chatbotSessionId') || generateSessionId();
let chatbotMessages = [];
let isChatbotOpen = false;

// Initialize chatbot on page load
function loadChatHistory() {
    // Only fetch history if the user is actually logged in
    // You can check for a specific element only visible to logged-in users
    if (!document.querySelector('.bottom-nav')) return; 
    
    fetch(`/chatbot/history?session_id=${chatbotSessionId}`)}

   
document.addEventListener('DOMContentLoaded', function() {
    loadChatHistory();
    setupChatbotEventListeners();
});

// Generate unique session ID
function generateSessionId() {
    const sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('chatbotSessionId', sessionId);
    return sessionId;
}

// Toggle chatbot visibility
function toggleChatbot() {
    const container = document.getElementById('chatbotContainer');
    const widget = document.getElementById('chatbotWidget');
    
    isChatbotOpen = !isChatbotOpen;
    
    if (isChatbotOpen) {
        container.style.display = 'flex';
        widget.classList.add('open');
        // Focus input
        setTimeout(() => {
            document.getElementById('chatbotInput').focus();
        }, 300);
        // Load suggestions
        loadQuickSuggestions();
    } else {
        container.style.display = 'none';
        widget.classList.remove('open');
    }
}

// Setup event listeners
function setupChatbotEventListeners() {
    // Enter key to send message
    document.getElementById('chatbotInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendChatMessage();
        }
    });
    
    // Close chatbot when clicking outside (optional)
    document.addEventListener('click', function(e) {
        if (isChatbotOpen && !e.target.closest('.chatbot-widget')) {
            // Don't close automatically - let user close manually
        }
    });
}

// Send message to chatbot
function sendChatMessage() {
    const input = document.getElementById('chatbotInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Clear input
    input.value = '';
    
    // Add user message to UI
    addMessageToChat('user', message);
    
    // Get current page for context
    const currentPage = getCurrentPage();
    
    // Show typing indicator
    showTypingIndicator();
    
    // Send to server
    fetch('/chatbot/message', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message: message,
            session_id: chatbotSessionId,
            page: currentPage
        })
    })
    .then(response => response.json())
    .then(data => {
        // Remove typing indicator
        hideTypingIndicator();
        
        if (data.success) {
            // Add bot response to UI
            addMessageToChat('bot', data.response);
            
            // Update quick replies
            if (data.quick_replies) {
                updateQuickReplies(data.quick_replies);
            }
            
            // Save session ID
            if (data.session_id) {
                chatbotSessionId = data.session_id;
                localStorage.setItem('chatbotSessionId', chatbotSessionId);
            }
        } else {
            addMessageToChat('bot', 'Sorry, I encountered an error. Please try again.');
        }
    })
    .catch(error => {
        hideTypingIndicator();
        addMessageToChat('bot', 'Network error. Please check your connection.');
        console.error('Chatbot error:', error);
    });
}

// Add message to chat UI
function addMessageToChat(sender, message) {
    const messagesContainer = document.getElementById('chatbotMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    // Format message with line breaks and basic markdown
    const formattedMessage = formatMessage(message);
    messageDiv.innerHTML = formattedMessage;
    
    messagesContainer.appendChild(messageDiv);
    
    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    // Store in local array
    chatbotMessages.push({
        sender: sender,
        message: message,
        timestamp: new Date().toISOString()
    });
}

// Format message with basic markdown and emojis
function formatMessage(message) {
    // Convert markdown-style bold
    message = message.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Convert markdown-style italic
    message = message.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Convert URLs to links
    message = message.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank">$1</a>');
    
    // Convert line breaks to <br>
    message = message.replace(/\n/g, '<br>');
    
    // Add emoji support
    message = addEmojis(message);
    
    return message;
}

// Add emojis to text
function addEmojis(text) {
    const emojiMap = {
        ':\)': '😊',
        ':\(' : '😢',
        '<3': '❤️',
        ':thumbsup:' : '👍',
        ':check:' : '✅',
        ':warning:' : '⚠️',
        ':bulb:' : '💡',
        ':chart:' : '📊',
        ':money:' : '💰',
        ':phone:' : '📱',
        ':file:' : '📄',
        ':print:' : '🖨️',
        ':save:' : '💾',
        ':delete:' : '🗑️',
        ':edit:' : '✏️',
        ':search:' : '🔍',
        ':time:' : '⏰',
        ':calendar:' : '📅',
        ':help:' : '❓',
        ':info:' : 'ℹ️'
    };
    
    for (let [key, value] of Object.entries(emojiMap)) {
        text = text.replace(new RegExp(key, 'g'), value);
    }
    
    return text;
}

// Show typing indicator
function showTypingIndicator() {
    const messagesContainer = document.getElementById('chatbotMessages');
    const indicator = document.createElement('div');
    indicator.className = 'message bot typing-indicator';
    indicator.id = 'typingIndicator';
    indicator.innerHTML = '<span>.</span><span>.</span><span>.</span>';
    messagesContainer.appendChild(indicator);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Hide typing indicator
function hideTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
        indicator.remove();
    }
}

// Load quick suggestions
function loadQuickSuggestions() {
    const currentPage = getCurrentPage();
    
    fetch(`/chatbot/suggestions?page=${currentPage}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateQuickReplies(data.suggestions);
            }
        })
        .catch(error => console.error('Error loading suggestions:', error));
}

// Update quick reply buttons
function updateQuickReplies(suggestions) {
    const container = document.querySelector('.chatbot-suggestions');
    if (!container) return;
    
    container.innerHTML = '';
    
    suggestions.forEach(suggestion => {
        const button = document.createElement('button');
        button.className = 'quick-reply-btn';
        button.textContent = suggestion;
        button.onclick = () => {
            document.getElementById('chatbotInput').value = suggestion;
            sendChatMessage();
        };
        container.appendChild(button);
    });
}

// Quick question handler
function quickQuestion(question) {
    document.getElementById('chatbotInput').value = question;
    sendChatMessage();
}

// Get current page for context
function getCurrentPage() {
    const path = window.location.pathname;
    if (path.includes('dashboard')) return 'dashboard';
    if (path.includes('transactions')) return 'transactions';
    if (path.includes('reports')) return 'reports';
    if (path.includes('categories')) return 'categories';
    if (path.includes('add')) return 'add_transaction';
    return 'other';
}

// Load chat history
function loadChatHistory() {
    if (!currentUser) return; // Only if user is logged in
    
    fetch(`/chatbot/history?session_id=${chatbotSessionId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.history.length > 0) {
                // Clear existing messages
                const container = document.getElementById('chatbotMessages');
                container.innerHTML = '';
                
                // Add welcome message if no history
                if (data.history.length === 0) {
                    addWelcomeMessage();
                } else {
                    // Load last 10 messages
                    const recentHistory = data.history.slice(0, 10).reverse();
                    recentHistory.forEach(item => {
                        addMessageToChat('user', item.message);
                        addMessageToChat('bot', item.response);
                    });
                }
            } else {
                addWelcomeMessage();
            }
        })
        .catch(() => {
            addWelcomeMessage();
        });
}

// Add welcome message
function addWelcomeMessage() {
    const currentLang = document.documentElement.lang || 'en';
    const welcome = currentLang === 'en' 
        ? "Hello! 👋 I'm your LedgerMate assistant. How can I help you today?"
        : "Habari! 👋 Mimi ni msaidizi wako wa LedgerMate. Nikusaidie vipi leo?";
    
    addMessageToChat('bot', welcome);
}

// Clear chat history
function clearChatHistory() {
    if (confirm('Clear conversation history?')) {
        fetch('/chatbot/clear', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: chatbotSessionId
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Clear UI
                document.getElementById('chatbotMessages').innerHTML = '';
                addWelcomeMessage();
                
                // Generate new session
                chatbotSessionId = generateSessionId();
            }
        });
    }
}

// Rate response
function rateResponse(chatId, helpful) {
    fetch('/chatbot/feedback', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            chat_id: chatId,
            helpful: helpful
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Thank you for your feedback!');
        }
    });
}
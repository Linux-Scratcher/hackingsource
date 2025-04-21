document.addEventListener('DOMContentLoaded', function() {
    const socket = io({
        auth: {
            user_id: user_id,
            username: username
        }
    });

    const messageInput = document.getElementById('message');
    const sendBtn = document.getElementById('send-btn');
    const messagesContainer = document.getElementById('messages');
    const usersList = document.getElementById('users-list');

    // Focus automatique sur le champ message
    messageInput.focus();

    function sendMessage() {
        const message = messageInput.value.trim();
        
        if (message) {
            socket.emit('chat_message', {
                message: message
            }, function(ack) {
                if (ack && ack.status === 'ok') {
                    messageInput.value = '';
                }
            });
        }
    }

    // Gestionnaires d'événements
    sendBtn.addEventListener('click', sendMessage);
    
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Réception des messages
    socket.on('chat_message', function(data) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', 'user');
        messageElement.innerHTML = `<strong>> ${data.username} [${data.timestamp}]:</strong> ${data.message}`;
        messagesContainer.appendChild(messageElement);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    });

    // Messages système
    socket.on('system_message', function(data) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', 'system');
        messageElement.textContent = `> Système: ${data.message}`;
        messagesContainer.appendChild(messageElement);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    });

    // Mise à jour des utilisateurs connectés
    socket.on('update_users', function(users) {
        usersList.innerHTML = '';
        users.forEach(user => {
            const userElement = document.createElement('li');
            userElement.textContent = `> ${user}`;
            usersList.appendChild(userElement);
        });
    });

    // Gestion des erreurs
    socket.on('connect_error', (err) => {
        console.error('Erreur de connexion:', err);
        alert('Erreur de connexion au serveur de chat');
    });

    // Confirmation d'envoi de message
    socket.on('message_ack', (data) => {
        if (data.status === 'ok') {
            messageInput.value = '';
        }
    });
});

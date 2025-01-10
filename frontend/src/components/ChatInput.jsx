import { useState } from 'react';
import { Box, TextField, IconButton } from '@mui/material';
import { Send } from '@mui/icons-material';

function ChatInput({ sessionId, onSendMessage, disabled, placeholder }) {
    const [message, setMessage] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        if (message.trim() && !disabled) {
            onSendMessage(message);
            setMessage('');
        }
    };

    return (
        <Box 
            component="form" 
            onSubmit={handleSubmit}
            sx={{
                display: 'flex',
                gap: 1,
                alignItems: 'center'
            }}
        >
            <TextField
                sx={{ flex: 1 }}
                size="small"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder={placeholder || "Enter your task..."}
                variant="outlined"
                disabled={disabled}
            />
            <IconButton 
                type="submit" 
                color="primary" 
                disabled={disabled}
                sx={{ flexShrink: 0 }}
            >
                <Send />
            </IconButton>
        </Box>
    );
}

export default ChatInput; 
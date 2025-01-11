import axios from 'axios';
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    Typography,
    Box,
    IconButton,
    Popover,
  } from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';
import LiveAgentConsole from './LiveAgentConsole';
import ChatInput from './ChatInput';
import { useState } from 'react';
  
  function SessionDialog({ session, onClose, onSessionStop }) {
    const [chatHistory, setChatHistory] = useState([]);
    const [anchorEl, setAnchorEl] = useState(null);
    const [isProcessing, setIsProcessing] = useState(false);

    const handleInfoClick = (event) => {
        setAnchorEl(event.currentTarget);
    };

    const handleInfoClose = () => {
        setAnchorEl(null);
    };

    const open = Boolean(anchorEl);

    if (!session) return null;
  
    const handleStopSession = async () => {
      try {
        await axios.delete(`/api/sessions/${session.session_id}`);
        onClose();
        if (onSessionStop) {
          onSessionStop();
        }
      } catch (error) {
        console.error('Error stopping session:', error);
      }
    };
  
    const handleSendMessage = async (message) => {
        try {
            setIsProcessing(true);
          
            
            // Add message to chat history
            setChatHistory(prev => [...prev, { type: 'human', content: message }]);
            
            // Send to backend
            await axios.post(`/api/sessions/${session.session_id}/chat`, null, {
                params: { message }
            });
        } catch (error) {
            console.error('Error sending message:', error);
        }
    };
  
    return (
      <Dialog open={!!session} onClose={onClose} maxWidth="xl" fullWidth>
        <DialogTitle sx={{ 
            display: 'flex', 
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 1
        }}>
            <Typography component="div" variant="h6">
                Session {session.session_id}
            </Typography>
            <IconButton 
                onClick={handleInfoClick}
                size="small"
                color="primary"
            >
                <InfoIcon />
            </IconButton>
            <Popover
                open={open}
                anchorEl={anchorEl}
                onClose={handleInfoClose}
                anchorOrigin={{
                    vertical: 'bottom',
                    horizontal: 'right',
                }}
                transformOrigin={{
                    vertical: 'top',
                    horizontal: 'right',
                }}
            >
                <Box sx={{ p: 2, maxWidth: 300 }}>
                    <Typography variant="subtitle2" gutterBottom>Session Details</Typography>
                    <Typography variant="body2">Resolution: {session.resolution}</Typography>
                    <Typography variant="body2">Debug Port: {session.debug_port}</Typography>
                    <Typography variant="body2">VNC Port: {session.vnc_port}</Typography>
                </Box>
            </Popover>
        </DialogTitle>
        <DialogContent>
          {session.status === 'running' ? (
            <Box sx={{ 
              display: 'flex',
              flexDirection: 'column',
              height: 'calc(75vh - 100px)',
              gap: 2
            }}>
              <Box sx={{ 
                display: 'grid',
                gridTemplateColumns: '3fr 2fr',
                gap: 2,
                flex: 1,
                overflow: 'hidden'
              }}>
                <Box sx={{
                  bgcolor: '#000',
                  borderRadius: 1,
                  overflow: 'hidden',
                  height: '100%',
                  '& iframe': {
                    width: '100%',
                    height: '100%',
                    border: 'none',
                  }
                }}>
                  <iframe
                    src={`http://127.0.0.1:${session.vnc_port}/vnc.html?resize=scale`}
                    allow="clipboard-read; clipboard-write"
                    title="VNC Session"
                  />
                </Box>

                {session.tag === 'samthropic' && (
                  <Box sx={{ 
                    height: '100%',
                    overflow: 'hidden'
                  }}>
                    <LiveAgentConsole sessionId={session.session_id} />
                  </Box>
                )}
              </Box>

              {session.tag === 'samthropic' && (
                <Box sx={{ 
                  width: '100%',
                  maxWidth: '800px',
                  mx: 'auto'
                }}>
                  <ChatInput 
                    sessionId={session.session_id} 
                    onSendMessage={handleSendMessage}
                    disabled={isProcessing}
                    placeholder={isProcessing ? "Processing..." : "Enter your task..."}
                  />
                </Box>
              )}
            </Box>
          ) : (
            <Box sx={{ height: 'calc(70vh - 100px)' }}>
              <Typography variant="h6" gutterBottom>
                Session Recording
              </Typography>
              <Box sx={{
                height: 'calc(100% - 32px)',
                bgcolor: '#000',
                borderRadius: 1,
                overflow: 'hidden',
              }}>
                <video 
                  controls 
                  width="100%" 
                  height="100%"
                  src={`/api/videos/${session.session_id}`}
                  style={{ objectFit: 'contain' }}
                />
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          {session.status === 'running' && (
            <Button 
              onClick={() => handleStopSession(session.session_id)}
              color="error"
            >
              Stop Session
            </Button>
          )}
          <Button onClick={onClose}>Close</Button>
        </DialogActions>
      </Dialog>
    );
  }
  
  export default SessionDialog;
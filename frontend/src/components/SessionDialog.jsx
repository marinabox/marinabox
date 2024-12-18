import axios from 'axios';
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    Typography,
    Box,
  } from '@mui/material';
  
  function SessionDialog({ session, onClose, onSessionStop }) {
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
  
    return (
      <Dialog open={!!session} onClose={onClose} maxWidth="lg" fullWidth>
        <DialogTitle>
          Session Details - {session.session_id}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ mb: 2 }}>
            <Typography variant="body1" gutterBottom>
              Status: {session.status}
            </Typography>
            <Typography variant="body1" gutterBottom>
              Resolution: {session.resolution}
            </Typography>
            <Typography variant="body1" gutterBottom>
              Debug Port: {session.debug_port}
            </Typography>
            <Typography variant="body1" gutterBottom>
              VNC Port: {session.vnc_port}
            </Typography>
          </Box>
          
          {session.status === 'running' && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="h6" gutterBottom>
                Live Session
              </Typography>
              <Box
                sx={{
                  position: 'relative',
                  width: '100%',
                  height: '60vh',
                  bgcolor: '#000',
                  borderRadius: 1,
                  overflow: 'hidden',
                  '& iframe': {
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    border: 'none',
                  }
                }}
              >
                <iframe
                  src={`http://127.0.0.1:${session.vnc_port}/vnc.html?resize=scale`}
                  allow="clipboard-read; clipboard-write"
                  title="VNC Session"
                />
              </Box>
            </Box>
          )}

          {session.video_path && (
            <Box>
              <Typography variant="h6" gutterBottom>
                Session Recording
              </Typography>
              <video 
                controls 
                width="100%" 
                src={`/api/videos/${session.session_id}`}
                preload="auto"
                style={{
                  backgroundColor: '#000',
                  maxHeight: '60vh',
                  objectFit: 'contain'
                }}
                controlsList="nodownload"
                playsInline
                onLoadedMetadata={(e) => {
                  const video = e.target;
                  // Force metadata reload
                  if (video.duration === Infinity) {
                    video.currentTime = 1e101;
                    video.currentTime = 0;
                  }
                }}
                onSeeking={(e) => {
                  const video = e.target;
                  // If seeking fails, try to recover
                  if (video.currentTime === 0) {
                    video.load();
                    video.play();
                  }
                }}
              />
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          {session.status === 'running' && (
            <Button 
              onClick={handleStopSession}
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
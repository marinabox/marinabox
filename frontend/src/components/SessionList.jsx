import {
    Grid,
    Card,
    CardContent,
    Typography,
    Chip,
    Box,
  } from '@mui/material';
  import { formatDistanceToNow, parseISO } from 'date-fns';
  
  const formatRuntime = (seconds) => {
    console.log('Raw runtime seconds:', seconds);
    seconds = Math.round(seconds);
    console.log('Rounded runtime seconds:', seconds);
    
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = seconds % 60;
      console.log(`Converting to minutes: ${minutes}m ${remainingSeconds}s`);
      return `${minutes}m ${remainingSeconds}s`;
    }
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    console.log(`Converting to hours: ${hours}h ${minutes}m`);
    return `${hours}h ${minutes}m`;
  };
  
  function SessionList({ sessions, onSessionClick }) {
    return (
      <Grid container spacing={2}>
        {sessions.map((session) => (
          <Grid item xs={12} sm={6} md={4} key={session.session_id}>
            <Card 
              sx={{ 
                cursor: 'pointer',
                '&:hover': { bgcolor: 'background.paper' },
                border: session.tag === 'samthropic' ? '2px solid #1a237e' : 'none',
              }}
              onClick={() => onSessionClick(session)}
            >
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  {session.tag === 'samthropic' ? 'Samthropic Agent' : `Session ${session.session_id}`}
                </Typography>
                <Box sx={{ mb: 1 }}>
                  <Chip
                    label={session.status}
                    color={session.status === 'running' ? 'success' : 'default'}
                    size="small"
                    sx={{ mr: 1 }}
                  />
                  <Chip
                    label={session.resolution}
                    color="primary"
                    size="small"
                    sx={{ mr: 1 }}
                  />
                  {session.tag === 'samthropic' && (
                    <Chip
                      label="AI Agent"
                      color="secondary"
                      size="small"
                    />
                  )}
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Created {formatDistanceToNow(parseISO(session.created_at))} ago
                </Typography>
                {session.status === 'running' && (
                  <Typography variant="body2" color="text.secondary">
                    Runtime: {formatRuntime(session.runtime_seconds)}
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    );
  }
  
  export default SessionList;
import { useState, useEffect } from 'react';
import {
  Box,
  Tabs,
  Tab,
  Container,
  Typography,
  Paper,
} from '@mui/material';
import SessionList from './SessionList';
import SessionDialog from './SessionDialog';
import axios from 'axios';

function Dashboard() {
  const [tab, setTab] = useState(0);
  const [sessions, setSessions] = useState([]);
  const [closedSessions, setClosedSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [samthropicSession, setSamthropicSession] = useState(null);

  const fetchSessions = async () => {
    try {
      const [activeSessions, closedSessions] = await Promise.all([
        axios.get('/api/sessions'),
        axios.get('/api/sessions/closed'),
      ]);
      setSessions(activeSessions.data);
      setClosedSessions(closedSessions.data);
    } catch (error) {
      console.error('Error fetching sessions:', error);
    }
  };

  useEffect(() => {
    fetchSessions();
    const interval = setInterval(fetchSessions, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleTabChange = (event, newValue) => {
    setTab(newValue);
  };

  const handleSessionClick = (session) => {
    setSelectedSession(session);
  };

  const handleCloseDialog = () => {
    setSelectedSession(null);
  };

  const getDisplaySessions = () => {
    switch (tab) {
      case 0:
        return sessions;
      case 1:
        return closedSessions;
      case 2:
        return [...sessions, ...closedSessions];
      default:
        return [];
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" gutterBottom sx={{ 
        color: 'primary.main', 
        display: 'flex', 
        alignItems: 'center',
        gap: 2  // Adds space between logo and text
      }}>
        <img src="/logo.png" alt="MarinaBox Logo" style={{ height: '40px' }} />
        MarinaBox
      </Typography>

      <Paper sx={{ mb: 2 }}>
        <Tabs value={tab} onChange={handleTabChange} centered>
          <Tab label="Running Sessions" />
          <Tab label="Closed Sessions" />
          <Tab label="All Sessions" />
        </Tabs>
      </Paper>
      
      <SessionList 
        sessions={getDisplaySessions()} 
        onSessionClick={handleSessionClick}
      />
      
      <SessionDialog
        session={selectedSession}
        onClose={handleCloseDialog}
        onSessionStop={fetchSessions}
      />
    </Container>
  );
}

export default Dashboard;
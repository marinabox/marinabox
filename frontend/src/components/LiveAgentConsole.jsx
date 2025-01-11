import { useEffect, useRef, useState } from 'react';
import { Box, Paper, Typography, IconButton } from '@mui/material';
import { Psychology, DarkMode, LightMode } from '@mui/icons-material';
import axios from 'axios';

function LiveAgentConsole({ sessionId }) {
    const [consoleOutput, setConsoleOutput] = useState([]);
    const [isDarkMode, setIsDarkMode] = useState(true);
    const consoleEndRef = useRef(null);
    const eventSourceRef = useRef(null);

    // useEffect(() => {
    //     if (sessionId) {
    //         const fetchConsoleOutput = async () => {
    //             try {
    //                 console.log('Fetching console output for session:', sessionId);
    //                 const response = await axios.get(`/console/${sessionId}`);
    //                 console.log('Received response:', response);
                    
    //                 if (response.data.output) {
    //                     setConsoleOutput(response.data.output);
    //                 }
    //             } catch (error) {
    //                 console.error('Error fetching console output:', error);
    //             }
    //         };

    //         // Initial fetch
    //         fetchConsoleOutput();

    //         // Set up interval and store its ID
    //         intervalRef.current = setInterval(fetchConsoleOutput, 1000);

    //         // Cleanup function
    //         return () => {
    //             if (intervalRef.current) {
    //                 clearInterval(intervalRef.current);
    //                 intervalRef.current = null;
    //             }
    //         };
    //     }
    // }, [sessionId]);
    useEffect(() => {
        if (sessionId) {
            // Update API paths to include /api prefix
            const loadInitialOutput = async () => {
                try {
                    const response = await axios.get(`/api/console/${sessionId}`);
                    if (response.data.output) {
                        setConsoleOutput(response.data.output);
                    }
                } catch (error) {
                    console.error('Error fetching initial console output:', error);
                }
            };
            
            loadInitialOutput();

            // Set up SSE connection with /api prefix
            const setupEventSource = () => {
                const eventSource = new EventSource(`api/console/stream/${sessionId}`);
                
                eventSource.onmessage = (event) => {
                    setConsoleOutput(prev => [...prev, event.data + '\n']);
                };

                eventSource.onerror = (error) => {
                    console.error('EventSource failed:', error);
                    eventSource.close();
                    // Attempt to reconnect after a delay
                    setTimeout(setupEventSource, 5000);
                };

                eventSourceRef.current = eventSource;
            };

            setupEventSource();

            // Cleanup function
            return () => {
                if (eventSourceRef.current) {
                    eventSourceRef.current.close();
                    eventSourceRef.current = null;
                }
            };
        }
    }, [sessionId]);

    // Auto-scroll to bottom when new content arrives
    useEffect(() => {
        if (consoleEndRef.current) {
            consoleEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [consoleOutput]);

    const toggleDarkMode = () => {
        setIsDarkMode(!isDarkMode);
    };

    return (
        <Paper
            sx={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                bgcolor: isDarkMode ? '#1a1a1a' : '#ffffff',
                color: isDarkMode ? '#fff' : '#000',
                overflow: 'hidden'
            }}
        >
            <Box sx={{ 
                padding: "2px", 
                borderBottom: '1px solid',
                borderColor: isDarkMode ? '#333' : '#e0e0e0',
                bgcolor: isDarkMode ? '#000' : '#f5f5f5',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
            }}>
                <Typography variant="h6" sx={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: 1,
                    color: isDarkMode ? '#fff' : '#000'
                }}>
                    <Psychology /> Agent Console
                </Typography>
                <IconButton 
                    onClick={toggleDarkMode}
                    sx={{ color: isDarkMode ? '#fff' : '#000' }}
                >
                    {isDarkMode ? <LightMode /> : <DarkMode />}
                </IconButton>
            </Box>
            
            <Box 
                sx={{ 
                    flex: 1, 
                    overflow: 'auto',
                    p: 2,
                    fontFamily: 'monospace',
                    fontSize: '0.9rem',
                    whiteSpace: 'pre-wrap',
                    bgcolor: isDarkMode ? '#1a1a1a' : '#ffffff',
                    '&::-webkit-scrollbar': {
                        width: '8px'
                    },
                    '&::-webkit-scrollbar-thumb': {
                        backgroundColor: isDarkMode ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.2)',
                        borderRadius: '4px'
                    }
                }}
            >
                {consoleOutput.map((line, index) => (
                    <Typography 
                        key={index} 
                        component="div"
                        sx={{ 
                            mb: 1,
                            color: line.includes('SAMS THOUGHT:') ? 
                                (isDarkMode ? '#66b2ff' : '#0059b2') :
                                line.includes('SCREEN DESCRIPTION:') ? 
                                (isDarkMode ? '#98ee99' : '#2e7d32') :
                                line.includes('COMMAND TO THE COMPUTER GUY:') ? 
                                (isDarkMode ? '#ff9999' : '#c62828') :
                                (isDarkMode ? '#fff' : '#000')
                        }}
                    >
                        {line}
                    </Typography>
                ))}
                <div ref={consoleEndRef} />
            </Box>
        </Paper>
    );
}

export default LiveAgentConsole; 
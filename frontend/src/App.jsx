import { useState } from 'react';
import { ThemeProvider, CssBaseline } from '@mui/material';
import { createTheme } from '@mui/material/styles';
import Dashboard from './components/Dashboard';

const lightTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1a237e', // Dark blue
      light: '#534bae',
      dark: '#000051',
    },
    secondary: {
      main: '#0277bd', // Light blue
    },
    background: {
      default: '#f5f5f7', // Light grayish background
      paper: '#ffffff',   // White cards/components
    },
    text: {
      primary: '#1a237e', // Dark blue text
      secondary: '#455a64', // Bluish gray text
    },
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 2px 4px rgba(26, 35, 126, 0.1)', // Subtle blue shadow
          '&:hover': {
            boxShadow: '0 4px 8px rgba(26, 35, 126, 0.2)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          boxShadow: '0 2px 4px rgba(26, 35, 126, 0.1)',
        },
      },
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={lightTheme}>
      <CssBaseline />
      <Dashboard />
    </ThemeProvider>
  );
}

export default App;
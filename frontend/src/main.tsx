import React from 'react'
import ReactDOM from 'react-dom/client'
import '@fontsource-variable/jetbrains-mono'
import App from './App'
import './index.css'

document.title = `MagenticLite ${__APP_VERSION__}`

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)

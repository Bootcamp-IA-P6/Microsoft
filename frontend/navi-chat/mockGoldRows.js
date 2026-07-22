import ChatWindow from './components/ChatWindow';
import './App.css';

export default function App() {
  return (
    <div className="app">
      <a href="#main-content" className="skip-link">
        Saltar al contenido principal
      </a>

      <header className="app__header">
        <h1>Navi</h1>
        <p>Tu copiloto de movilidad</p>
      </header>

      <main id="main-content">
        <ChatWindow />
      </main>

      <footer className="app__footer">
        <p>Datos EMT Madrid · zona Puerta del Sol (600m)</p>
      </footer>
    </div>
  );
}

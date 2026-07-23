// NaviMascot: centraliza la referencia a la imagen de la mascota, para que
// solo haya que cambiar UNA ruta cuando Iris suba el archivo real.
//
// ⚠️ PENDIENTE: colocar el archivo real en `public/navi-mascot.png/svg`
// (mismo nombre exacto, o cambiar MASCOT_SRC abajo). Hasta entonces,
// esto muestra un emoji de bus como placeholder visual — no rompe el
// layout ni dependemos de un <img> roto en la demo.

const MASCOT_SRC = '/navi-mascot.svg';

export default function NaviMascot({ size = 40, className = '' }) {
  return (
    <span
      className={`navi-mascot ${className}`}
      style={{ width: size, height: size }}
      role="img"
      aria-label="Navi, el copiloto de movilidad"
    >
      <img
        src={MASCOT_SRC}
        alt=""
        onError={(e) => {
          // Si todavía no subieron el PNG real, escondemos el <img> roto
          // y mostramos el emoji placeholder que ya está en el DOM detrás.
          e.currentTarget.style.display = 'none';
        }}
      />
      <span aria-hidden="true" className="navi-mascot__placeholder">
        🚌
      </span>
    </span>
  );
}

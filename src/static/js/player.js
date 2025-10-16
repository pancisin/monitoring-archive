document.addEventListener('DOMContentLoaded', () => {
    const player = new Plyr('#player', {
          hideControls: false,
          fullscreen: { enabled: true, fallback: true },
    });
});
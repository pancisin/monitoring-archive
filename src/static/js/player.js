const createControl =  (label, handler) => {
    const button = document.createElement('button');
    button.className = 'plyr__control';
    button.innerHTML = label;
    button.title = label;
    button.onclick = handler;
    button.class = "user-select-none"

    return button;
}

document.addEventListener('DOMContentLoaded', () => {
    const fps = 10;
    const player = new Plyr('#player', {
          hideControls: false,
          fullscreen: { enabled: true, fallback: true },
           controls: [
            'play', 'progress', 'current-time', 'duration', 'settings', 'fullscreen', 'prevframe', 'nextframe'
          ]
    });

    const controls = document.querySelector('.plyr__controls');

    const prevBtn = createControl("<", () => {
        player.pause();
        player.currentTime -= 1 / fps;
    })
    controls.appendChild(prevBtn);

    const nextBtn = createControl(">", () => {
        player.pause();
        player.currentTime += 1 / fps;
    });
    controls.appendChild(nextBtn);
});
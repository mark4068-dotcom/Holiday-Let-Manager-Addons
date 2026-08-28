const YOUTUBE_CONTROLS_ID = "crossjack-youtube-volume-controls";

function installYoutubeControls(video) {
  if (document.getElementById(YOUTUBE_CONTROLS_ID)) {
    return;
  }

  const controls = document.createElement("div");
  controls.id = YOUTUBE_CONTROLS_ID;

  const down = document.createElement("button");
  down.type = "button";
  down.textContent = "Volume −";
  down.setAttribute("aria-label", "Reduce video volume");

  const level = document.createElement("output");
  level.setAttribute("aria-live", "polite");

  const up = document.createElement("button");
  up.type = "button";
  up.textContent = "Volume +";
  up.setAttribute("aria-label", "Increase video volume");

  function showLevel() {
    level.textContent = video.muted
      ? "Muted"
      : `${Math.round(video.volume * 100)}%`;
  }

  function changeVolume(amount) {
    video.muted = false;
    video.volume = Math.max(0, Math.min(1, video.volume + amount));
    showLevel();
  }

  down.addEventListener("click", () => changeVolume(-0.1));
  up.addEventListener("click", () => changeVolume(0.1));
  video.addEventListener("volumechange", showLevel);

  const pauseVideo = () => {
    if (!video.paused) {
      video.pause();
    }
  };
  window.addEventListener("blur", pauseVideo);
  window.addEventListener("pagehide", pauseVideo);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      pauseVideo();
    }
  });

  controls.append(down, level, up);
  document.body.appendChild(controls);
  showLevel();
}

function findVideo() {
  const video = document.querySelector("video");
  if (video) {
    installYoutubeControls(video);
    return true;
  }
  return false;
}

if (!findVideo()) {
  const observer = new MutationObserver(() => {
    if (findVideo()) {
      observer.disconnect();
    }
  });
  observer.observe(document.documentElement, { childList: true, subtree: true });
}

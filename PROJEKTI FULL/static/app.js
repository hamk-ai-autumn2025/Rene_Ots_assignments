const form = document.getElementById('storyForm');
const storyCard = document.getElementById('storyCard');
const selects = document.querySelectorAll('.option-card select');
const downloadBtn = document.getElementById('downloadBtn');
const arrowButtons = document.querySelectorAll('.card-arrow');

const updateSelectImage = (select) => {
  const targetId = select.dataset.imageTarget;
  if (!targetId) return;
  const imageElement = document.getElementById(targetId);
  if (!imageElement) return;
  const option = select.options[select.selectedIndex];
  if (option?.dataset?.image) {
    imageElement.src = option.dataset.image;
  }

  const altPrefix = select.dataset.imageAltPrefix || '';
  if (option?.value) {
    imageElement.alt = `${altPrefix}${option.value}`;
  }
};

const updateDisplay = (select) => {
  const display = document.querySelector(`[data-display="${select.name}"]`);
  if (display) {
    display.textContent = select.value;
  }

  updateSelectImage(select);
};

selects.forEach((select) => {
  updateDisplay(select);
select.addEventListener('change', () => updateDisplay(select));
});

const cycleSelect = (select, direction) => {
  if (!select) return;
  const total = select.options.length;
  if (!total) return;
  let newIndex = select.selectedIndex + direction;
  if (newIndex >= total) newIndex = 0;
  if (newIndex < 0) newIndex = total - 1;
  select.selectedIndex = newIndex;
  select.dispatchEvent(new Event('change'));
};

arrowButtons.forEach((button) => {
  button.addEventListener('click', () => {
    const target = document.getElementById(button.dataset.target);
    const direction = Number(button.dataset.direction) || 1;
    cycleSelect(target, direction);
  });
});

const renderStory = (text) => {
  const paragraphs = text
    .split(/\n+/)
    .map((chunk) => chunk.trim())
    .filter(Boolean);

  storyCard.innerHTML = `
    <h2>Your Story</h2>
    ${paragraphs.map((p) => `<p>${p}</p>`).join('')}
  `;
};

const renderMessage = (message) => {
  storyCard.innerHTML = `<p class="story-placeholder">${message}</p>`;
};

const setDownloadState = (enabled) => {
  if (!downloadBtn) return;
  downloadBtn.disabled = !enabled;
};

let latestStory = '';
let latestDetails = null;

form.addEventListener('submit', (event) => {
  event.preventDefault();

  const lengthInput = form.querySelector('input[name="length"]:checked');

  const payload = {
    character: form.character.value,
    setting: form.setting.value,
    genre: form.genre.value,
    tone: form.tone.value,
    length: lengthInput ? lengthInput.value : 'short',
  };

  setDownloadState(false);
  renderMessage('Creating a whimsical story for you...');
  storyCard.querySelector('p').classList.add('loading');

  fetch('/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
    .then(async (response) => {
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || 'Unable to create a story right now.');
      }
      return response.json();
    })
    .then((data) => {
      if (data.story) {
        renderStory(data.story);
        latestStory = data.story;
        latestDetails = {
          character: payload.character,
          setting: payload.setting,
          genre: payload.genre,
          tone: payload.tone,
          lengthLabel: data.lengthLabel || '',
        };
        setDownloadState(true);
      } else {
        latestStory = '';
        latestDetails = null;
        renderMessage('Something went wrong. Please try again!');
      }
    })
    .catch((error) => {
      latestStory = '';
      latestDetails = null;
      renderMessage(error.message);
    });
});

if (downloadBtn) {
  downloadBtn.addEventListener('click', () => {
    if (!latestStory || !latestDetails) return;

    const originalText = downloadBtn.textContent;
    downloadBtn.textContent = 'Preparing PDF...';
    downloadBtn.disabled = true;

    fetch('/download', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        story: latestStory,
        details: latestDetails,
      }),
    })
      .then(async (response) => {
        if (!response.ok) {
          const data = await response.json().catch(() => ({}));
          throw new Error(data.error || 'Unable to create PDF right now.');
        }
        return response.blob();
      })
      .then((blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'ai-kids-story.pdf';
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      })
      .catch((error) => {
        alert(error.message);
      })
      .finally(() => {
        downloadBtn.textContent = originalText;
        downloadBtn.disabled = false;
      });
  });
}

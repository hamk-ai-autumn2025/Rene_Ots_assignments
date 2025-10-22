const API_ENDPOINT = 'https://api.openai.com/v1/images/generations';
const API_KEY =

const generatorForm = document.getElementById('generator-form');
const promptInput = document.getElementById('prompt');
const negativePromptInput = document.getElementById('negative-prompt');
const guidanceInput = document.getElementById('guidance');
const guidanceValue = document.getElementById('guidance-value');
const generateButton = document.getElementById('generate-button');
const previewContainer = document.getElementById('preview-container');
const downloadButton = document.getElementById('download-button');

const STORAGE_KEYS = {
  prompt: 'ai-image-last-prompt',
  aspect: 'ai-image-aspect',
};

let generatedImage = null;

const aspectInputs = [...document.querySelectorAll('input[name="aspect"]')];

function restoreState() {
  const savedPrompt = localStorage.getItem(STORAGE_KEYS.prompt);
  const savedAspect = localStorage.getItem(STORAGE_KEYS.aspect);

  if (savedPrompt) promptInput.value = savedPrompt;

  if (savedAspect) {
    const match = aspectInputs.find((input) => input.value === savedAspect);
    if (match) match.checked = true;
  }
}

function setLoading(isLoading) {
  generateButton.disabled = isLoading;
  generateButton.classList.toggle('is-loading', isLoading);
}

function setPreviewContent(node) {
  previewContainer.replaceChildren(node);
}

function setPreviewPlaceholder(message = 'Generated images will appear here.') {
  const span = document.createElement('span');
  span.className = 'preview-text';
  span.textContent = message;
  previewContainer.className = 'preview-placeholder';
  setPreviewContent(span);
  downloadButton.disabled = true;
  generatedImage = null;
}

function setPreviewError(message) {
  const errorBlock = document.createElement('div');
  errorBlock.className = 'preview-placeholder';
  const title = document.createElement('strong');
  title.textContent = 'Generation failed';
  const text = document.createElement('p');
  text.textContent = message;
  errorBlock.append(title, text);
  previewContainer.className = 'preview-placeholder';
  setPreviewContent(errorBlock);
  downloadButton.disabled = true;
  generatedImage = null;
}

function setPreviewImage(src) {
  const img = document.createElement('img');
  img.src = src;
  img.alt = 'Generated artwork';
  img.className = 'preview-image';
  previewContainer.className = 'preview-image-wrap';
  setPreviewContent(img);
  generatedImage = src;
  downloadButton.disabled = false;
}

function getSelectedAspect() {
  const checked = aspectInputs.find((input) => input.checked);
  return checked ? checked.value : '1:1';
}

function persistFormState() {
  localStorage.setItem(STORAGE_KEYS.prompt, promptInput.value);
  localStorage.setItem(STORAGE_KEYS.aspect, getSelectedAspect());
}

async function generateImage(payload) {
  const headers = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${API_KEY}`,
  };

  const response = await fetch(API_ENDPOINT, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Request failed with status ${response.status}`);
  }

  const data = await response.json();
  return data;
}

function resolveImageSource(data) {
  if (data.imageUrl) {
    return data.imageUrl;
  }

  if (data.image_base64) {
    return `data:image/png;base64,${data.image_base64}`;
  }

  if (data.images && Array.isArray(data.images) && data.images.length > 0) {
    const first = data.images[0];
    if (typeof first === 'string' && first.startsWith('http')) {
      return first;
    }
    if (typeof first === 'string') {
      return `data:image/png;base64,${first}`;
    }
    if (first.url) {
      return first.url;
    }
    if (first.base64) {
      return `data:image/png;base64,${first.base64}`;
    }
  }

  if (data.data && Array.isArray(data.data) && data.data.length > 0) {
    const first = data.data[0];
    if (first.url) {
      return first.url;
    }
    if (first.b64_json) {
      return `data:image/png;base64,${first.b64_json}`;
    }
  }

  throw new Error('Response does not include an image URL or base64 payload.');
}

generatorForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  persistFormState();
  setLoading(true);
  setPreviewPlaceholder('Generating image...');

  const negativePrompt = negativePromptInput.value.trim();
  const guidance = Number(guidanceInput.value);
  const payload = {
    model: 'gpt-image-1',
    prompt: promptInput.value.trim(),
    size: mapAspectToSize(getSelectedAspect()),
    quality: mapGuidanceToQuality(guidance),
  };

  if (negativePrompt) {
    payload.negative_prompt = negativePrompt;
  }

  try {
    const result = await generateImage(payload);
    const src = resolveImageSource(result);
    setPreviewImage(src);
  } catch (error) {
    setPreviewError(error.message);
  } finally {
    setLoading(false);
  }
});

guidanceInput.addEventListener('input', () => {
  guidanceValue.textContent = guidanceInput.value;
});

downloadButton.addEventListener('click', () => {
  if (!generatedImage) return;

  const link = document.createElement('a');

  if (generatedImage.startsWith('data:')) {
    link.href = generatedImage;
    link.download = `ai-image-${Date.now()}.png`;
  } else {
    link.href = generatedImage;
    link.download = '';
  }

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
});

restoreState();
setPreviewPlaceholder();

function mapAspectToSize(aspect) {
  switch (aspect) {
    case '16:9':
      return '1792x1024';
    case '9:16':
      return '1024x1792';
    case '3:2':
      return '1792x1024';
    default:
      return '1024x1024';
  }
}

function mapGuidanceToQuality(value) {
  if (value >= 15) return 'high';
  if (value >= 8) return 'medium';
  return 'low';
}

const form = document.querySelector('#project-form');
const topic = document.querySelector('#topic');
const counter = document.querySelector('#counter');
const result = document.querySelector('#result');
const submit = document.querySelector('#submit');
const apiDialog = document.querySelector('#api-dialog');
const apiForm = document.querySelector('#api-form');
const apiStatus = document.querySelector('#api-status');
const apiMessage = document.querySelector('#api-message');
const saveApi = document.querySelector('#save-api');

topic.addEventListener('input', () => {
  counter.textContent = `${topic.value.length}/500`;
});

document.querySelectorAll('.style-card').forEach((card) => {
  card.addEventListener('click', () => {
    document.querySelectorAll('.style-card').forEach((item) => item.classList.remove('selected'));
    card.classList.add('selected');
  });
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  result.hidden = true;
  result.classList.remove('error');
  submit.disabled = true;
  submit.firstElementChild.textContent = 'Criando...';

  const data = Object.fromEntries(new FormData(form).entries());
  try {
    const response = await fetch('/api/projects', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Não foi possível criar o projeto.');

    result.innerHTML = `<strong>Projeto criado com sucesso ✓</strong>
      Estilo escolhido: ${escapeHtml(payload.style_label)}.<br>
      Brief salvo em <code>${escapeHtml(payload.brief_path)}</code>.<br>
      Nenhuma API foi chamada e nenhum vídeo foi renderizado.
      <button class="generate-script" type="button" data-project="${escapeHtml(payload.project)}" data-episode="${payload.episode}">
        <span>Gerar roteiro com IA</span><span>→</span>
      </button>
      <div class="generation-status"></div>`;
    result.hidden = false;
    result.scrollIntoView({behavior: 'smooth', block: 'center'});
  } catch (error) {
    result.textContent = error.message;
    result.classList.add('error');
    result.hidden = false;
  } finally {
    submit.disabled = false;
    submit.firstElementChild.textContent = 'Criar projeto';
  }
});

result.addEventListener('click', async (event) => {
  const button = event.target.closest('.generate-script');
  if (!button) return;
  const accepted = window.confirm('Gerar o roteiro agora? Esta ação consumirá uma pequena parte do saldo da sua API Anthropic.');
  if (!accepted) return;

  const status = result.querySelector('.generation-status');
  button.disabled = true;
  button.firstElementChild.textContent = 'Gerando roteiro...';
  status.textContent = 'A IA está escrevendo. Isso pode levar alguns minutos; não feche esta página.';
  try {
    const response = await fetch(`/api/projects/${button.dataset.project}/episodes/${button.dataset.episode}/script`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: '{}',
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Não foi possível gerar o roteiro.');
    button.remove();
    status.innerHTML = `<strong>Roteiro concluído ✓</strong>
      ${escapeHtml(payload.word_count)} palavras · modelo ${escapeHtml(payload.model)}.<br>
      Salvo em <code>${escapeHtml(payload.script_path)}</code>.`;
    status.classList.add('success');
  } catch (error) {
    button.disabled = false;
    button.firstElementChild.textContent = 'Tentar gerar novamente';
    status.textContent = error.message;
    status.classList.add('error');
  }
});

function escapeHtml(value) {
  const node = document.createElement('div');
  node.textContent = value ?? '';
  return node.innerHTML;
}

document.querySelector('#open-api').addEventListener('click', () => apiDialog.showModal());
document.querySelector('#close-api').addEventListener('click', () => apiDialog.close());

async function refreshSettings() {
  try {
    const response = await fetch('/api/settings');
    const payload = await response.json();
    if (payload.anthropic.configured) {
      apiStatus.textContent = `Conectada · ${payload.anthropic.masked_key}`;
      apiStatus.classList.add('connected');
      document.querySelector('#open-api').textContent = 'Alterar';
    }
  } catch (_) {
    apiStatus.textContent = 'Não foi possível verificar';
  }
}

apiForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  apiMessage.textContent = '';
  apiMessage.classList.remove('success');
  saveApi.disabled = true;
  saveApi.firstElementChild.textContent = 'Testando...';
  try {
    const response = await fetch('/api/settings/anthropic', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({api_key: document.querySelector('#api-key').value}),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Não foi possível conectar.');
    document.querySelector('#api-key').value = '';
    apiMessage.textContent = payload.message;
    apiMessage.classList.add('success');
    await refreshSettings();
    setTimeout(() => apiDialog.close(), 1200);
  } catch (error) {
    apiMessage.textContent = error.message;
  } finally {
    saveApi.disabled = false;
    saveApi.firstElementChild.textContent = 'Testar e salvar';
  }
});

refreshSettings();
